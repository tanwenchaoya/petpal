from __future__ import annotations

from typing import Any


def build_basic_petpal_tools(servo_controler: Any) -> list[Any]:
    from robocrew.core.tools import finish_task
    from robocrew.robots.XLeRobot.tools import create_move_forward, create_turn_left, create_turn_right

    return [
        create_move_forward(servo_controler),
        create_turn_left(servo_controler),
        create_turn_right(servo_controler),
        finish_task,
    ]
