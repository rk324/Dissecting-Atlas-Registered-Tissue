FSR = "full size reference"
DSR = "downscale reference"
FSL = "full size label"
DSL = "downscale label"

DEFAULT_STALIGN_PARAMS = {
            'timesteps': 12,
            'iterations': 100,
            'sigmaM': 0.5,
            'sigmaP': 1,
            'sigmaR': 1e8,
            'resolution': 250
        }

ALPHA = 1.5
BACKGROUND_PERCENTILE = 60

COMMITTED_COLOR = 'lime'
REMOVABLE_COLOR = 'orange'
NEW_COLOR = 'red'