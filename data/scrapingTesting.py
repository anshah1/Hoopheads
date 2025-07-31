from nba_api.stats.static import players
from nba_api.stats.endpoints import commonplayerinfo
import time

doncic_data = commonplayerinfo.CommonPlayerInfo(1629029)
print(doncic_data.expected_data.keys())