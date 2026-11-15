from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent/'src'))
from tavernlens.app import main
raise SystemExit(main())
