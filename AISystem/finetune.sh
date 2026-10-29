#!/bin/bash
#SBATCH -p GPU                  # partition (queue)
#SBATCH -N 1                    # number of nodes
#SBATCH -t 0-08:00              # time (D-HH:MM)
#SBATCH -o slurm.%N.%j.out      # STDOUT
#SBATCH -e slurm.%N.%j.err      # STDERR
#SBATCH --gres=gpu:1

# make conda available inside the batch job
if [ -f "/usr/local/anaconda3/etc/profile.d/conda.sh" ]; then
    . "/usr/local/anaconda3/etc/profile.d/conda.sh"
else
    export PATH="/usr/local/anaconda3/bin:$PATH"
fi
source activate torchgpu  

cd "$SLURM_SUBMIT_DIR"
export USE_TF=0 USE_FLAX=0
nvidia-smi
python finetune.py --config model_config.json


