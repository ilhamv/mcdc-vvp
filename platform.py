"""
Supported compute platforms and their parameters
"""

PLATFORMS = ["dane", "lassen", "tuolumne"]

JOB_SUBMISSION = {}
JOB_SUBMISSION["dane"] = 'sbatch'
JOB_SUBMISSION["lassen"] = 'bsub'
JOB_SUBMISSION["tuolumne"] = 'flux batch'

JOB_SCHEDULER = {}
JOB_SCHEDULER["dane"] = 'slurm'
JOB_SCHEDULER["lassen"] = 'lsf'
JOB_SCHEDULER["tuolumne"] = 'flux'

JOB_TIME = {}
JOB_TIME['dane'] = "XX:00:00"
JOB_TIME['lassen'] = "XX:00"
JOB_TIME['tuolumne'] = "XXh"

MAX_TIME = {}
MAX_TIME['dane'] = 24
MAX_TIME['lassen'] = 24 # Actual max: 12
MAX_TIME['tuolumne'] = 24

CPU_CORES_PER_NODE = {}
CPU_CORES_PER_NODE["dane"] = 112
CPU_CORES_PER_NODE["lassen"] = 40 # 44
CPU_CORES_PER_NODE["tuolumne"] = 96

GPUS_PER_NODE = {}
GPUS_PER_NODE["dane"] = 0
GPUS_PER_NODE["lassen"] = 4
GPUS_PER_NODE["tuolumne"] = 4

MAX_NODES = {}
MAX_NODES["dane"] = 128 # Actual limit: 520
MAX_NODES["lassen"] = 128 # Actual limit: 256
MAX_NODES["tuolumne"] = 128 # No strict limit
