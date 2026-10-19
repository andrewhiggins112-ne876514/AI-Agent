import unittest
from queue import Queue
from unittest.mock import Mock, patch

from scripts.task_execution import (
    PlanValidationError,
    StepState,
    Task,
    TaskEventType,
    TaskState,
    TaskStep,
    preflight_actions,
    run_task,
    transition_step_state,
    transition_task_state,
)
from scripts import tools


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

        result = run_task(task, event_queue, execute)
        events = self.read_events(event_queue)

        self.assertEqual(result.state, TaskState.SUCCEEDED)
        self.assertEqual(executed, ["OPEN_NOTEPAD", "TYPE_TEXT"])
        self.assertEqual(
            [step.state for step in task.steps],
            [StepState.SUCCEEDED, StepState.SUCCEEDED],
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

        def execute(action):
            executed.append(action["action"])
            return {"ok": False, "error": "simulated failure"}

        result = run_task(task, event_queue, execute)
        events = self.read_events(event_queue)

        self.assertEqual(result.state, TaskState.FAILED)
        self.assertEqual(executed, ["OPEN_NOTEPAD"])
        self.assertEqual(task.steps[0].state, StepState.FAILED)
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


if __name__ == "__main__":
    unittest.main()
