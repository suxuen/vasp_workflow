#!/bin/bash
{% if queue_type == "slurm" %}#SBATCH -J {{ name }}
#SBATCH --time={{ time }}:00:00
#SBATCH -o {{ name }}.o%j
#SBATCH -e {{ name }}.e%j
#SBATCH --mem={{ mem }}
#SBATCH --tasks {{ tasks }}
#SBATCH --nodes {{ nodes }}
#SBATCH --ntasks-per-node {{ ppn }}
{% if nodes == 1 and computer == "janus"%}#SBATCH --reservation=janus-serial {% endif %}
{% if computer == "summit" %}#SBATCH --qos {{ queue }}
#SBATCH --export=NONE
#SBATCH -N {{ nodes }} {% endif %}
{% if computer == "eagle" %}#SBATCH --account={{ account }} {% endif %}
{% elif queue_type == "pbs" %}#PBS -j eo
#PBS -l nodes={{ nodes }}:ppn={{ ppn }}{% if computer == "psiops" %}:{{ queue }}{% endif %}
#PBS -l walltime={{ time }}:00:00
#PBS -q {% if computer == "psiops" %}batch{% else %}{{ queue }}{% endif %}
#PBS -N {{ name }}
{% if computer == "peregrine" %}#PBS -A {{ account }}{% endif %}
cd $PBS_O_WORKDIR
echo $PBS_O_WORKDIR{% endif %}

{% block environment %}
# Set Environment
source {{ vasp_bashrc }}
export OMP_NUM_THREADS={{ openmp }} {% endblock environment %}

{% block vasp %}
python -c "
{% block python %}
from custodian.vasp.jobs import *
from custodian.vasp.handlers import *
from custodian.custodian import *
from Classes_Custodian import *

incar = Incar.from_file('INCAR')

if 'AUTO_GAMMA' in incar and incar['AUTO_GAMMA']:
    vasp = '{{ vasp_gamma }}'
else:
    vasp = '{{ vasp_kpts }}'

vaspjob = [{{ jobtype }}Job(['{{ mpi }}',{% if mpi != "srun" %} '-np', '{{ tasks }}',{% endif %} vasp], '{{ logname }}', auto_npar=False, backup=False)]

{% if jobtype == "NEB" %}
handlers = [WalltimeHandler({{ time }}*60*60, 15*60)]

{% elif jobtype == "Dimer" %}
handlers = [WalltimeHandler({{ time }}*60*60, 15*60), NEBNotTerminating('{{ logname }}', 180*60),
            DimerDivergingHandler(), DimerCheckMins(), UnconvergedErrorHandler()]

{% elif jobtype == "Standard" %}
handlers = [WalltimeHandler({{ time }}*60*60), UnconvergedErrorHandler()]
{% endif %}

c = Custodian(handlers, vaspjob, max_errors=1000, skip_over_errors=True)
c.run()
{% endblock python %}
"
{% endblock vasp %}
