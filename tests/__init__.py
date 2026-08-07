# -*- coding: utf-8 -*-
"""
Goi tests/ - noi chua toan bo test tu dong cho du an AntWorld.

CACH CHAY:
    python -m unittest discover -s tests -v
    # hoac neu da cai pytest (khong bat buoc):
    python -m pytest tests -v

File __init__.py nay CHAY TRUOC MOI test module (vi Python luon import
package truoc khi import module con ben trong) - dung de bat buoc pygame
chay o che do "dummy" (khong can man hinh that/loa that). Nho vay test co
the chay duoc tren may khong co man hinh (CI, terminal thuan qua SSH...)
ma khong bi treo cho o pygame.display.set_mode().

Neu ban dang chay tren may co man hinh va MUON test mo cua so that de
nhin bang mat, dat bien moi truong ANTWORLD_TEST_REAL_DISPLAY=1 truoc khi
chay (vi du de debug 1 test render cu the).
"""
import os

if os.environ.get("ANTWORLD_TEST_REAL_DISPLAY") != "1":
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
