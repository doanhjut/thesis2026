"""
PID Adaptive Fusion
===================
Dong gop loi #1 — Luan van Thac si
"Phat hien Ransomware bang XAI va Active Learning"

Dung hop diem tinh (P_static, LightGBM/EMBER) va diem dong
(P_dynamic, Honeypot/Sandbox) bang bo dieu khien PID.

    e(t) = P_static - P_dynamic
    u(t) = Kp*e(t) + Ki*sum(e) + Kd*de/dt
    w_static = clip(sigmoid(u(t)), 0.1, 0.9)
    P_fused  = w_static * P_static + (1 - w_static) * P_dynamic

He so mac dinh dung trong thuc nghiem: Kp=0.85, Ki=0.12, Kd=0.35.
"""

from __future__ import annotations

import numpy as np

DEFAULT_KP = 0.85
DEFAULT_KI = 0.12
DEFAULT_KD = 0.35


class PIDController:
    """Bo dieu khien PID cho co che Adaptive Fusion.

    Dieu chinh trong so nhanh Static (LightGBM) dua tren sai so giua
    diem Static va diem Dynamic (Honeypot). Muc tieu: on dinh quyet dinh
    khi hai nguon thong tin bat dong, trong khi giu do tre ~15 ms.
    """

    def __init__(
        self,
        kp: float = DEFAULT_KP,
        ki: float = DEFAULT_KI,
        kd: float = DEFAULT_KD,
        setpoint: float = 0.0,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.prev_error = 0.0
        self.integral = 0.0

    def reset(self) -> None:
        """Xoa trang thai tich phan va sai so truoc do."""
        self.prev_error = 0.0
        self.integral = 0.0

    def update(self, error: float) -> float:
        """Cap nhat PID voi sai so hien tai, tra ve w_static trong (0.1, 0.9)."""
        self.integral += error
        derivative = error - self.prev_error
        control = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        w_static = 1.0 / (1.0 + np.exp(-control))
        return float(np.clip(w_static, 0.1, 0.9))


def fuse_scores(p_static: float, p_dynamic: float, w_static: float) -> float:
    """Dung hop hai xac suat. w_dynamic = 1 - w_static."""
    w_static = float(np.clip(w_static, 0.0, 1.0))
    return float(w_static * p_static + (1.0 - w_static) * p_dynamic)
