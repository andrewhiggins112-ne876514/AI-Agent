import tempfile
import unittest
from pathlib import Path
from queue import Queue
from unittest.mock import Mock, patch

from scripts import task_execution
from scripts.tools import ForegroundWindowSnapshot
from scripts.task_execution import (
    PlanValidationError,
    StepState,
    Task,
    TaskEventType,
    TaskState,
    TaskStep,
    VerificationResult,
    VerificationStatus,
    preflight_actions,
    run_task,
    transition_step_state,
    transition_task_state,
    verify_action,
)
from scripts import tools
from scripts.target_awareness import (
    TargetConfidence,
    TargetIdentity,
    TargetMatchStatus,
)


class ForegroundWindowObserverTests(unittest.TestCase):
    def test_snapshot_includes_title_handle_and_process_id(self):
        with (
            patch.object(
                tools.win32gui,
                "GetForegroundWindow",
                return_value=1234,
            ),
            patch.object(
                tools.win32gui,
                "GetWindowText",
                return_value="Untitled - Notepad",
            ),
            patch.object(
                tools.win32process,
                "GetWindowThreadProcessId",
                return_value=(111, 5678),
            ),
        ):
            snapshot = tools.get_foreground_window_snapshot()

        self.assertEqual(snapshot.title, "Untitled - Notepad")
        self.assertEqual(snapshot.window_handle, 1234)
        self.assertEqual(snapshot.process_id, 5678)
        self.assertIsNone(snapshot.error)

    def test_snapshot_represents_no_foreground_window(self):
        with (
            patch.object(
                tools.win32gui,
                "GetForegroundWindow",
                return_value=0,
            ),
            patch.object(tools.win32gui, "GetWindowText") as get_title,
            patch.object(
                tools.win32process,
                "GetWindowThreadProcessId",
            ) as get_process,
        ):
            snapshot = tools.get_foreground_window_snapshot()

        self.assertEqual(snapshot, ForegroundWindowSnapshot())
        get_title.assert_not_called()
        get_process.assert_not_called()


class PreflightValidationTests(unittest.TestCase):
    def test_valid_action_list_is_accepted_without_running_tools(self):
        actions = [
            {"action": "OPEN_NOTEPAD", "params": {}},
            {"action": "TYPE_TEXT", "params": {"text": "hello"}},
        ]
        with patch.dict(
            tools.TOOL_MAP,
            {name: Mock() for name in tools.TOOL_MAP},
        ) as patched_tools:
            preflight_actions(actions)
            for tool in patched_tools.values():
                tool.assert_not_called()

    def test_invalid_later_action_rejects_whole_plan(self):
        actions = [
            {"action": "OPEN_NOTEPAD", "params": {}},
            {"action": "TYPE_TEXT", "params": {}},
        ]
        with patch.dict(
            tools.TOOL_MAP,
            {name: Mock() for name in tools.TOOL_MAP},
        ) as patched_tools:
            with self.assertRaises(PlanValidationError) as raised:
                preflight_actions(actions)

            self.assertEqual(raised.exception.step_index, 1)
            self.assertIn("Missing required parameter", str(raised.exception))
            for tool in patched_tools.values():
                tool.assert_not_called()

    def test_invalid_plan_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must be a list"):
            preflight_actions({"action": "OPEN_NOTEPAD", "params": {}})


class TaskStateTransitionTests(unittest.TestCase):
    def test_every_defined_task_transition_is_allowed(self):
        transitions = [
            (TaskState.RECEIVED, TaskState.VALIDATING),
            (TaskState.RECEIVED, TaskState.FAILED),
            (TaskState.VALIDATING, TaskState.READY),
            (TaskState.VALIDATING, TaskState.FAILED),
            (TaskState.READY, TaskState.RUNNING),
            (TaskState.READY, TaskState.FAILED),
            (TaskState.RUNNING, TaskState.SUCCEEDED),
            (TaskState.RUNNING, TaskState.PARTIAL),
            (TaskState.RUNNING, TaskState.FAILED),
        ]
        for initial_state, final_state in transitions:
            with self.subTest(initial=initial_state, final=final_state):
                task = Task(request="request", steps=[], state=initial_state)
                transition_task_state(task, final_state)
                self.assertEqual(task.state, final_state)

    def test_invalid_task_transition_is_rejected_without_mutation(self):
        task = Task(request="request", steps=[])

        with self.assertRaisesRegex(ValueError, "Illegal task state transition"):
            transition_task_state(task, TaskState.RUNNING)

        self.assertEqual(task.state, TaskState.RECEIVED)
        self.assertIsNone(task.started_at)

    def test_terminal_task_state_cannot_transition(self):
        task = Task(request="request", steps=[], state=TaskState.FAILED)

        with self.assertRaisesRegex(ValueError, "Illegal task state transition"):
            transition_task_state(task, TaskState.READY)

    def test_cancelled_state_has_no_transition_implementation(self):
        task = Task(request="request", steps=[])

        with self.assertRaisesRegex(ValueError, "Illegal task state transition"):
            transition_task_state(task, TaskState.CANCELLED)


class StepStateTransitionTests(unittest.TestCase):
    def test_every_defined_step_transition_is_allowed(self):
        transitions = [
            (StepState.PENDING, StepState.RUNNING),
            (StepState.PENDING, StepState.SKIPPED),
            (StepState.RUNNING, StepState.SUCCEEDED),
            (StepState.RUNNING, StepState.UNVERIFIED),
            (StepState.RUNNING, StepState.FAILED),
        ]
        for initial_state, final_state in transitions:
            with self.subTest(initial=initial_state, final=final_state):
                step = TaskStep(
                    action="TYPE_TEXT",
                    params={"text": "hello"},
                    state=initial_state,
                )
                transition_step_state(step, final_state)
                self.assertEqual(step.state, final_state)

    def test_running_and_terminal_timestamps_are_recorded(self):
        step = TaskStep(action="TYPE_TEXT", params={"text": "hello"})
        transition_step_state(step, StepState.RUNNING)
        self.assertIsNotNone(step.started_at)

        transition_step_state(step, StepState.UNVERIFIED)
        self.assertIsNotNone(step.finished_at)

    def test_invalid_step_transition_is_rejected_without_mutation(self):
        step = TaskStep(action="TYPE_TEXT", params={"text": "hello"})

        with self.assertRaisesRegex(ValueError, "Illegal step state transition"):
            transition_step_state(step, StepState.SUCCEEDED)

        self.assertEqual(step.state, StepState.PENDING)
        self.assertIsNone(step.started_at)

    def test_terminal_step_state_cannot_transition(self):
        step = TaskStep(
            action="TYPE_TEXT",
            params={"text": "hello"},
            state=StepState.FAILED,
        )

        with self.assertRaisesRegex(ValueError, "Illegal step state transition"):
            transition_step_state(step, StepState.RUNNING)


class SequentialTaskRunnerTests(unittest.TestCase):
    def setUp(self):
        observer_patch = patch.object(
            task_execution.tools,
            "get_foreground_window_snapshot",
            return_value=ForegroundWindowSnapshot(),
        )
        observer_patch.start()
        self.addCleanup(observer_patch.stop)

    def make_task(self):
        return Task(
            request="open notepad and type hello",
            steps=[
                TaskStep(action="OPEN_NOTEPAD", params={}),
                TaskStep(action="TYPE_TEXT", params={"text": "hello"}),
            ],
        )

    @staticmethod
    def read_events(event_queue):
        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())
        return events

    def test_successful_multistep_execution_is_ordered_and_emits_events(self):
        task = self.make_task()
        event_queue = Queue()
        executed = []

        def execute(action):
            executed.append(action["action"])
            return {"ok": True, "result": f"{action['action']} complete"}

        verification = VerificationResult(
            VerificationStatus.VERIFIED,
            "test outcome verified",
        )
        with patch(
            "scripts.task_execution.verify_action",
            return_value=verification,
        ):
            result = run_task(task, event_queue, execute)
        events = self.read_events(event_queue)

        self.assertEqual(result.state, TaskState.SUCCEEDED)
        self.assertEqual(executed, ["OPEN_NOTEPAD", "TYPE_TEXT"])
        self.assertEqual(
            [step.state for step in task.steps],
            [StepState.SUCCEEDED, StepState.SUCCEEDED],
        )
        self.assertTrue(
            all(step.verification_result is verification for step in task.steps)
        )
        self.assertEqual(
            [event.event_type for event in events],
            [
                TaskEventType.TASK_STARTED,
                TaskEventType.STEP_STARTED,
                TaskEventType.STEP_COMPLETED,
                TaskEventType.STEP_STARTED,
                TaskEventType.STEP_COMPLETED,
                TaskEventType.TASK_COMPLETED,
            ],
        )
        self.assertEqual(events[0].task_state, TaskState.VALIDATING)
        self.assertEqual(events[1].task_state, TaskState.RUNNING)
        self.assertEqual(events[1].step_state, StepState.RUNNING)
        self.assertEqual(
            events[-1].task_state,
            TaskState.SUCCEEDED,
        )

    def test_foreground_snapshot_is_attached_immediately_before_dispatch(self):
        task = Task(
            request="type hello",
            steps=[TaskStep(action="TYPE_TEXT", params={"text": "hello"})],
        )
        event_queue = Queue()
        snapshot = ForegroundWindowSnapshot(
            title="Untitled - Notepad",
            window_handle=1234,
            process_id=5678,
        )
        calls = []

        def observe():
            calls.append("observe")
            return snapshot

        def execute(action):
            calls.append("dispatch")
            return {"ok": True, "result": "Typed: hello"}

        result = run_task(
            task,
            event_queue,
            execute,
            window_observer=observe,
        )
        events = self.read_events(event_queue)
        step_started = next(
            event
            for event in events
            if event.event_type is TaskEventType.STEP_STARTED
        )

        self.assertEqual(calls, ["observe", "dispatch"])
        self.assertIs(step_started.foreground_window, snapshot)
        self.assertEqual(result.state, TaskState.PARTIAL)
        self.assertEqual(task.steps[0].state, StepState.UNVERIFIED)

    def test_no_foreground_window_snapshot_does_not_block_execution(self):
        task = Task(
            request="type hello",
            steps=[TaskStep(action="TYPE_TEXT", params={"text": "hello"})],
        )
        event_queue = Queue()
        no_window = ForegroundWindowSnapshot()
        executor = Mock(return_value={"ok": True, "result": "Typed: hello"})

        result = run_task(
            task,
            event_queue,
            executor,
            window_observer=lambda: no_window,
        )
        events = self.read_events(event_queue)
        step_started = next(
            event
            for event in events
            if event.event_type is TaskEventType.STEP_STARTED
        )

        self.assertIs(step_started.foreground_window, no_window)
        executor.assert_called_once()
        self.assertEqual(result.state, TaskState.PARTIAL)
        self.assertEqual(task.steps[0].state, StepState.UNVERIFIED)

    def test_observer_error_is_reported_without_changing_execution_outcome(self):
        task = Task(
            request="type hello",
            steps=[TaskStep(action="TYPE_TEXT", params={"text": "hello"})],
        )
        event_queue = Queue()
        executor = Mock(return_value={"ok": True, "result": "Typed: hello"})

        def observe():
            raise RuntimeError("foreground API unavailable")

        result = run_task(
            task,
            event_queue,
            executor,
            window_observer=observe,
        )
        events = self.read_events(event_queue)
        step_started = next(
            event
            for event in events
            if event.event_type is TaskEventType.STEP_STARTED
        )

        self.assertEqual(
            step_started.foreground_window.error,
            "RuntimeError: foreground API unavailable",
        )
        executor.assert_called_once()
        self.assertEqual(result.state, TaskState.PARTIAL)
        self.assertEqual(task.steps[0].state, StepState.UNVERIFIED)
        self.assertEqual(
            task.steps[0].verification_result.status,
            VerificationStatus.UNVERIFIED,
        )

    def test_invalid_plan_does_not_observe_foreground_window(self):
        task = Task(
            request="type",
            steps=[TaskStep(action="TYPE_TEXT", params={})],
        )
        event_queue = Queue()
        observer = Mock(return_value=ForegroundWindowSnapshot())
        executor = Mock()

        result = run_task(
            task,
            event_queue,
            executor,
            window_observer=observer,
        )

        observer.assert_not_called()
        executor.assert_not_called()
        self.assertEqual(result.state, TaskState.FAILED)

    def test_failure_stops_execution_and_skips_remaining_steps(self):
        task = Task(
            request="open app, type text, take screenshot",
            steps=[
                TaskStep(action="OPEN_NOTEPAD", params={}),
                TaskStep(action="TYPE_TEXT", params={"text": "hello"}),
                TaskStep(action="TAKE_SCREENSHOT", params={}),
            ],
        )
        event_queue = Queue()
        executed = []
        verifier = Mock()

        def execute(action):
            executed.append(action["action"])
            return {"ok": False, "error": "simulated failure"}

        with patch(
            "scripts.task_execution.verify_action",
            verifier,
        ):
            result = run_task(task, event_queue, execute)
        events = self.read_events(event_queue)

        self.assertEqual(result.state, TaskState.FAILED)
        self.assertEqual(executed, ["OPEN_NOTEPAD"])
        self.assertEqual(task.steps[0].state, StepState.FAILED)
        self.assertEqual(
            task.steps[0].verification_result.status,
            VerificationStatus.FAILED,
        )
        verifier.assert_not_called()
        self.assertEqual(
            [step.state for step in task.steps[1:]],
            [StepState.SKIPPED, StepState.SKIPPED],
        )
        self.assertEqual(
            [event.event_type for event in events],
            [
                TaskEventType.TASK_STARTED,
                TaskEventType.STEP_STARTED,
                TaskEventType.STEP_FAILED,
                TaskEventType.TASK_FAILED,
            ],
        )

    def test_executor_exception_stops_execution_and_emits_failure(self):
        task = self.make_task()
        event_queue = Queue()
        executed = []

        def execute(action):
            executed.append(action["action"])
            raise RuntimeError("tool crashed")

        result = run_task(task, event_queue, execute)
        events = self.read_events(event_queue)

        self.assertEqual(result.state, TaskState.FAILED)
        self.assertEqual(executed, ["OPEN_NOTEPAD"])
        self.assertEqual(task.steps[0].error, "tool crashed")
        self.assertEqual(task.steps[1].state, StepState.SKIPPED)
        self.assertEqual(events[-2].event_type, TaskEventType.STEP_FAILED)
        self.assertEqual(events[-1].event_type, TaskEventType.TASK_FAILED)

    def test_event_order_has_started_before_steps_and_terminal_last(self):
        task = self.make_task()
        event_queue = Queue()

        with patch(
            "scripts.task_execution.verify_action",
            return_value=VerificationResult(
                VerificationStatus.VERIFIED,
                "verified",
            ),
        ):
            run_task(
                task,
                event_queue,
                lambda action: {"ok": True, "result": action["action"]},
            )
        events = self.read_events(event_queue)

        self.assertEqual(events[0].event_type, TaskEventType.TASK_STARTED)
        self.assertEqual(events[-1].event_type, TaskEventType.TASK_COMPLETED)
        self.assertEqual(
            [
                event.step_index
                for event in events
                if event.event_type is TaskEventType.STEP_STARTED
            ],
            [0, 1],
        )
        self.assertEqual(
            [
                event.step_index
                for event in events
                if event.event_type is TaskEventType.STEP_COMPLETED
            ],
            [0, 1],
        )

    def test_invalid_plan_fails_before_executor_and_emits_task_failure(self):
        task = Task(
            request="open notepad and type",
            steps=[
                TaskStep(action="OPEN_NOTEPAD", params={}),
                TaskStep(action="TYPE_TEXT", params={}),
            ],
        )
        event_queue = Queue()
        executor = Mock(return_value={"ok": True})

        result = run_task(task, event_queue, executor)
        events = self.read_events(event_queue)

        self.assertEqual(result.state, TaskState.FAILED)
        executor.assert_not_called()
        self.assertEqual(
            [event.event_type for event in events],
            [TaskEventType.TASK_STARTED, TaskEventType.TASK_FAILED],
        )

    def test_matched_task_target_allows_typing_and_remains_unverified(self):
        target = TargetIdentity(process_id=5678)
        snapshot = ForegroundWindowSnapshot(
            title="Untitled - Notepad",
            window_handle=1234,
            process_id=5678,
        )
        task = self.make_task()
        event_queue = Queue()
        executed = []

        def execute(action):
            executed.append(action["action"])
            if action["action"] == "OPEN_NOTEPAD":
                return {
                    "ok": True,
                    "result": "Opened Notepad",
                    "target_identity": target,
                }
            return {"ok": True, "result": "Typed: hello"}

        def verify(action, outcome):
            if action["action"] == "OPEN_NOTEPAD":
                return VerificationResult(
                    VerificationStatus.VERIFIED,
                    "Notepad opened",
                )
            return VerificationResult(
                VerificationStatus.UNVERIFIED,
                "Typing cannot be read back",
            )

        with patch("scripts.task_execution.verify_action", side_effect=verify):
            result = run_task(
                task,
                event_queue,
                execute,
                window_observer=lambda: snapshot,
            )
        events = self.read_events(event_queue)
        typing_started = next(
            event
            for event in events
            if event.event_type is TaskEventType.STEP_STARTED
            and event.action == "TYPE_TEXT"
        )
        typing_completed = next(
            event
            for event in events
            if event.event_type is TaskEventType.STEP_COMPLETED
            and event.action == "TYPE_TEXT"
        )

        self.assertEqual(executed, ["OPEN_NOTEPAD", "TYPE_TEXT"])
        self.assertIs(task.target_identity, target)
        self.assertEqual(
            task.steps[1].target_assessment.status,
            TargetMatchStatus.MATCHED,
        )
        self.assertIs(
            typing_started.target_assessment,
            task.steps[1].target_assessment,
        )
        self.assertIs(
            typing_completed.target_assessment,
            task.steps[1].target_assessment,
        )
        self.assertEqual(
            task.steps[1].verification_result.status,
            VerificationStatus.UNVERIFIED,
        )
        self.assertEqual(result.state, TaskState.PARTIAL)

    def test_target_mismatch_blocks_typing_and_skips_remaining_steps(self):
        task = Task(
            request="open notepad, type hello, take screenshot",
            steps=[
                TaskStep(action="OPEN_NOTEPAD", params={}),
                TaskStep(action="TYPE_TEXT", params={"text": "hello"}),
                TaskStep(action="TAKE_SCREENSHOT", params={}),
            ],
        )
        event_queue = Queue()
        target = TargetIdentity(process_id=5678)
        snapshot = ForegroundWindowSnapshot(process_id=9012)
        executed = []

        def execute(action):
            executed.append(action["action"])
            return {
                "ok": True,
                "result": "Opened Notepad",
                "target_identity": target,
            }

        with patch(
            "scripts.task_execution.verify_action",
            return_value=VerificationResult(
                VerificationStatus.VERIFIED,
                "Notepad opened",
            ),
        ):
            result = run_task(
                task,
                event_queue,
                execute,
                window_observer=lambda: snapshot,
            )
        events = self.read_events(event_queue)
        typing_failed = next(
            event
            for event in events
            if event.event_type is TaskEventType.STEP_FAILED
            and event.action == "TYPE_TEXT"
        )

        self.assertEqual(executed, ["OPEN_NOTEPAD"])
        self.assertEqual(result.state, TaskState.FAILED)
        self.assertEqual(task.steps[1].state, StepState.FAILED)
        self.assertEqual(task.steps[2].state, StepState.SKIPPED)
        self.assertIsNone(task.steps[1].verification_result)
        self.assertEqual(
            typing_failed.target_assessment.status,
            TargetMatchStatus.MISMATCH,
        )
        self.assertFalse(typing_failed.result["dispatched"])
        self.assertEqual(len(result.result), 2)
        self.assertEqual(result.result[0]["action"], "OPEN_NOTEPAD")

    def test_unknown_task_target_preserves_typing_behavior(self):
        task = Task(
            request="type hello",
            steps=[TaskStep(action="TYPE_TEXT", params={"text": "hello"})],
        )
        event_queue = Queue()
        executor = Mock(return_value={"ok": True, "result": "Typed: hello"})

        result = run_task(
            task,
            event_queue,
            executor,
            window_observer=lambda: ForegroundWindowSnapshot(process_id=99),
        )
        events = self.read_events(event_queue)
        typing_started = next(
            event
            for event in events
            if event.event_type is TaskEventType.STEP_STARTED
        )

        executor.assert_called_once()
        self.assertEqual(result.state, TaskState.PARTIAL)
        self.assertEqual(
            typing_started.target_assessment.status,
            TargetMatchStatus.UNKNOWN,
        )
        self.assertEqual(
            task.steps[0].verification_result.status,
            VerificationStatus.UNVERIFIED,
        )

    def test_low_confidence_title_similarity_allows_typing_without_claiming_match(self):
        task = Task(
            request="type hello",
            steps=[TaskStep(action="TYPE_TEXT", params={"text": "hello"})],
            target_identity=TargetIdentity(title="Notepad"),
        )
        event_queue = Queue()
        executor = Mock(return_value={"ok": True, "result": "Typed: hello"})

        result = run_task(
            task,
            event_queue,
            executor,
            window_observer=lambda: ForegroundWindowSnapshot(title="notepad"),
        )

        executor.assert_called_once()
        self.assertEqual(result.state, TaskState.PARTIAL)
        self.assertEqual(
            task.steps[0].target_assessment.status,
            TargetMatchStatus.UNKNOWN,
        )
        self.assertEqual(
            task.steps[0].target_assessment.confidence,
            TargetConfidence.LOW,
        )
        self.assertEqual(
            task.steps[0].verification_result.status,
            VerificationStatus.UNVERIFIED,
        )

    def test_high_confidence_mismatch_blocks_typing_dispatch(self):
        task = Task(
            request="type hello",
            steps=[TaskStep(action="TYPE_TEXT", params={"text": "hello"})],
            target_identity=TargetIdentity(
                window_handle=1234,
                process_id=5678,
            ),
        )
        event_queue = Queue()
        executor = Mock(return_value={"ok": True, "result": "Typed: hello"})

        result = run_task(
            task,
            event_queue,
            executor,
            window_observer=lambda: ForegroundWindowSnapshot(
                window_handle=9012,
                process_id=3456,
            ),
        )
        events = self.read_events(event_queue)
        failed_event = next(
            event
            for event in events
            if event.event_type is TaskEventType.STEP_FAILED
        )

        executor.assert_not_called()
        self.assertEqual(result.state, TaskState.FAILED)
        self.assertEqual(
            failed_event.target_assessment.confidence,
            TargetConfidence.HIGH,
        )
        self.assertEqual(
            failed_event.target_assessment.status,
            TargetMatchStatus.MISMATCH,
        )


class NotepadTargetCaptureTests(unittest.TestCase):
    def test_execute_action_returns_launched_process_identity(self):
        with patch.object(
            tools.subprocess,
            "Popen",
            return_value=Mock(pid=5678),
        ) as popen:
            outcome = tools.execute_action(
                {"action": "OPEN_NOTEPAD", "params": {}}
            )

        popen.assert_called_once_with("notepad.exe")
        self.assertTrue(outcome["ok"])
        self.assertEqual(outcome["result"], "Opened Notepad")
        self.assertEqual(
            outcome["target_identity"],
            TargetIdentity(process_id=5678),
        )


class RunTaskVerificationTests(unittest.TestCase):
    def setUp(self):
        observer_patch = patch.object(
            task_execution.tools,
            "get_foreground_window_snapshot",
            return_value=ForegroundWindowSnapshot(),
        )
        observer_patch.start()
        self.addCleanup(observer_patch.stop)

    @staticmethod
    def make_task():
        return Task(
            request="open notepad and type hello",
            steps=[
                TaskStep(action="OPEN_NOTEPAD", params={}),
                TaskStep(action="TYPE_TEXT", params={"text": "hello"}),
            ],
        )

    @staticmethod
    def make_verification(status):
        return VerificationResult(status, f"{status.value} evidence")

    def test_verified_step_is_succeeded_and_recorded(self):
        task = self.make_task()
        event_queue = Queue()
        verification = self.make_verification(VerificationStatus.VERIFIED)

        with patch(
            "scripts.task_execution.verify_action",
            return_value=verification,
        ) as verifier:
            result = run_task(
                task,
                event_queue,
                lambda action: {"ok": True, "result": "done"},
            )

        self.assertEqual(result.state, TaskState.SUCCEEDED)
        self.assertEqual(task.steps[0].state, StepState.SUCCEEDED)
        self.assertIs(task.steps[0].verification_result, verification)
        verifier.assert_called()
        self.assertEqual(
            result.result[0]["verification"].status,
            VerificationStatus.VERIFIED,
        )

    def test_unverified_step_continues_and_task_is_partial(self):
        task = self.make_task()
        event_queue = Queue()
        verified = self.make_verification(VerificationStatus.VERIFIED)
        unverified = self.make_verification(VerificationStatus.UNVERIFIED)
        executions = []
        results = [verified, unverified]

        def execute(action):
            executions.append(action["action"])
            return {"ok": True, "result": "dispatched"}

        with patch(
            "scripts.task_execution.verify_action",
            side_effect=results,
        ):
            result = run_task(task, event_queue, execute)

        self.assertEqual(result.state, TaskState.PARTIAL)
        self.assertEqual(executions, ["OPEN_NOTEPAD", "TYPE_TEXT"])
        self.assertEqual(
            [step.state for step in task.steps],
            [StepState.SUCCEEDED, StepState.UNVERIFIED],
        )
        self.assertIs(task.steps[1].verification_result, unverified)
        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())
        self.assertEqual(
            [
                event.result["verification"].status
                for event in events
                if event.event_type is TaskEventType.STEP_COMPLETED
            ],
            [VerificationStatus.VERIFIED, VerificationStatus.UNVERIFIED],
        )
        self.assertEqual(
            [
                event.verification_result.status
                for event in events
                if event.event_type is TaskEventType.STEP_COMPLETED
            ],
            [VerificationStatus.VERIFIED, VerificationStatus.UNVERIFIED],
        )
        self.assertEqual(events[-1].task_state, TaskState.PARTIAL)

    def test_failed_verification_fails_task_and_skips_remaining_steps(self):
        task = Task(
            request="open notepad, type hello, take screenshot",
            steps=[
                TaskStep(action="OPEN_NOTEPAD", params={}),
                TaskStep(action="TYPE_TEXT", params={"text": "hello"}),
                TaskStep(action="TAKE_SCREENSHOT", params={}),
            ],
        )
        event_queue = Queue()
        failed_verification = self.make_verification(VerificationStatus.FAILED)
        executions = []

        def execute(action):
            executions.append(action["action"])
            return {"ok": True, "result": "tool call completed"}

        with patch(
            "scripts.task_execution.verify_action",
            return_value=failed_verification,
        ):
            result = run_task(task, event_queue, execute)

        self.assertEqual(result.state, TaskState.FAILED)
        self.assertEqual(executions, ["OPEN_NOTEPAD"])
        self.assertEqual(task.steps[0].state, StepState.FAILED)
        self.assertIs(task.steps[0].verification_result, failed_verification)
        self.assertEqual(
            [step.state for step in task.steps[1:]],
            [StepState.SKIPPED, StepState.SKIPPED],
        )
        self.assertEqual(
            result.result[0]["verification"].status,
            VerificationStatus.FAILED,
        )
        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())
        failed_step_event = next(
            event
            for event in events
            if event.event_type is TaskEventType.STEP_FAILED
        )
        self.assertEqual(failed_step_event.step_state, StepState.FAILED)
        self.assertEqual(
            failed_step_event.verification_result.status,
            VerificationStatus.FAILED,
        )
        self.assertEqual(events[-1].task_state, TaskState.FAILED)
        self.assertEqual(
            [event.event_type for event in events],
            [
                TaskEventType.TASK_STARTED,
                TaskEventType.STEP_STARTED,
                TaskEventType.STEP_FAILED,
                TaskEventType.TASK_FAILED,
            ],
        )


class ActionVerifierTests(unittest.TestCase):
    def test_notepad_verifier_reports_visible_notepad(self):
        with patch.object(tools, "get_windows", return_value=["Untitled - Notepad"]):
            result = verify_action(
                {"action": "OPEN_NOTEPAD", "params": {}},
                {"ok": True, "result": "Opened Notepad"},
            )

        self.assertEqual(result.status, VerificationStatus.VERIFIED)
        self.assertIn("Notepad", result.evidence)

    def test_notepad_verifier_fails_when_window_never_appears(self):
        with (
            patch.object(tools, "get_windows", return_value=["Calculator"]),
            patch.object(task_execution, "NOTEPAD_VERIFY_TIMEOUT_SECONDS", 0),
        ):
            result = verify_action(
                {"action": "OPEN_NOTEPAD", "params": {}},
                {"ok": True, "result": "Opened Notepad"},
            )

        self.assertEqual(result.status, VerificationStatus.FAILED)
        self.assertIn("No visible Notepad", result.evidence)

    def test_screenshot_verifier_checks_non_empty_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            screenshot = Path(temp_dir) / "capture.png"
            screenshot.write_bytes(b"image")
            with patch.object(task_execution, "SCREENSHOT_PATH", screenshot):
                result = verify_action(
                    {"action": "TAKE_SCREENSHOT", "params": {}},
                    {"ok": True, "result": "Screenshot saved"},
                )

        self.assertEqual(result.status, VerificationStatus.VERIFIED)
        self.assertIn("5 bytes", result.evidence)

    def test_screenshot_verifier_fails_for_missing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_screenshot = Path(temp_dir) / "missing.png"
            with patch.object(
                task_execution,
                "SCREENSHOT_PATH",
                missing_screenshot,
            ):
                result = verify_action(
                    {"action": "TAKE_SCREENSHOT", "params": {}},
                    {"ok": True, "result": "Screenshot saved"},
                )

        self.assertEqual(result.status, VerificationStatus.FAILED)
        self.assertIn("could not be inspected", result.evidence)

    def test_list_windows_verifier_accepts_list_result(self):
        result = verify_action(
            {"action": "LIST_WINDOWS", "params": {}},
            {"ok": True, "result": ["Notepad", "Explorer"]},
        )

        self.assertEqual(result.status, VerificationStatus.VERIFIED)
        self.assertIn("2 visible", result.evidence)

    def test_list_windows_verifier_rejects_invalid_result(self):
        result = verify_action(
            {"action": "LIST_WINDOWS", "params": {}},
            {"ok": True, "result": "Notepad"},
        )

        self.assertEqual(result.status, VerificationStatus.FAILED)

    def test_move_mouse_verifier_checks_requested_coordinates(self):
        with patch.object(tools.pyautogui, "position", return_value=(300, 200)):
            result = verify_action(
                {"action": "MOVE_MOUSE", "params": {"x": 300, "y": 200}},
                {"ok": True, "result": "Mouse moved"},
            )

        self.assertEqual(result.status, VerificationStatus.VERIFIED)

    def test_move_mouse_verifier_uses_default_coordinates(self):
        with patch.object(tools.pyautogui, "position", return_value=(500, 500)):
            result = verify_action(
                {"action": "MOVE_MOUSE", "params": {}},
                {"ok": True, "result": "Mouse moved"},
            )

        self.assertEqual(result.status, VerificationStatus.VERIFIED)

    def test_move_mouse_verifier_fails_on_coordinate_mismatch(self):
        with patch.object(tools.pyautogui, "position", return_value=(0, 0)):
            result = verify_action(
                {"action": "MOVE_MOUSE", "params": {"x": 300, "y": 200}},
                {"ok": True, "result": "Mouse moved"},
            )

        self.assertEqual(result.status, VerificationStatus.FAILED)

    def test_type_text_remains_unverified_by_design(self):
        result = verify_action(
            {"action": "TYPE_TEXT", "params": {"text": "hello"}},
            {"ok": True, "result": "Typed: hello"},
        )

        self.assertEqual(result.status, VerificationStatus.UNVERIFIED)
        self.assertIn("cannot be read back", result.evidence)

    def test_execution_failure_is_reported_by_verifier(self):
        result = verify_action(
            {"action": "TYPE_TEXT", "params": {"text": "hello"}},
            {"ok": False, "error": "tool failure"},
        )

        self.assertEqual(result.status, VerificationStatus.FAILED)
        self.assertEqual(result.evidence, "tool failure")

    def test_unknown_action_has_no_registered_verifier(self):
        with self.assertRaisesRegex(ValueError, "No verifier registered"):
            verify_action(
                {"action": "UNKNOWN", "params": {}},
                {"ok": True, "result": None},
            )


if __name__ == "__main__":
    unittest.main()
