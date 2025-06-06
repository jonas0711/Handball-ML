#!/usr/bin/env python3
"""
DEBUG SCRIPT FOR SEASONAL SYSTEM
"""

import os

base_dirs = ['Herreliga-database', 'Kvindeliga-database']
seasons = ['2018-2019', '2019-2020', '2020-2021', '2021-2022', '2022-2023', '2023-2024', '2024-2025', '2025-2026']

print('🔍 DEBUGGING SEASONAL SYSTEM:')
for base_dir in base_dirs:
    print(f'📁 Checking {base_dir}:')
    if os.path.exists(base_dir):
        available_seasons = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
        print(f'  ✅ Directory exists with seasons: {sorted(available_seasons)}')
        
        for season in seasons:
            season_path = os.path.join(base_dir, season)
            if os.path.exists(season_path):
                db_files = [f for f in os.listdir(season_path) if f.endswith('.db')]
                print(f'  📊 {season}: {len(db_files)} .db files')
            else:
                print(f'  ❌ {season}: ikke fundet')
    else:
        print(f'  ❌ Directory does not exist')

# Test master system import
print('\n🔍 TESTING MASTER SYSTEM IMPORT:')
try:
    from handball_elo_master import MasterHandballEloSystem
    print('✅ Master system can be imported')
    
    # Test instance creation
    master_system = MasterHandballEloSystem(".")
    print('✅ Master system instance created')
    
    # Test method exists
    if hasattr(master_system, 'process_season_database'):
        print('✅ process_season_database method exists')
    else:
        print('❌ process_season_database method missing')
        
except ImportError as e:
    print(f'❌ Import error: {e}')
except Exception as e:
    print(f'❌ Other error: {e}') 