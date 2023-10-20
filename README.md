# vasp_workflow
`vasp_workflow` can be used to rapidly generate and submit
[VASP](https://www.vasp.at/) jobs to SLURM supercomputing clusters. Currently
supported clusters include the National Renewable Energy Laboratory's (NREL)
[Eagle](https://www.nrel.gov/hpc/eagle-system.html), with plans to support
CU Boulder's [Summit](https://www.colorado.edu/rc/resources/summit) on the horizon.

## Overview

### Environmental Requirements (Perform Once)
1. Clone the repository into your home directory with the following command:
`git clone https://github.com/rymo1354/vasp_workflow.git`. You should now have
the `vasp_workflow` directory in your home directory.  

2. Append the absolute path of the `.../vasp_workflow` directory to the `$PATH` and `$PYTHONPATH` variables
within your `.bash_profile` or `.bashrc`. One of these should be in your home
directory. Do the same with the absolute path of `.../vasp_workflow/workflow_scripts`.
The absolute path can be found by navigating to the `vasp_workflow` directory and using the `pwd` command.

3. The file `.../vasp_workflow/vasp_run/vasp.py` uses scripts found in Ryan Trottier's
`VTST-Tools` directory. If this path isn't already in your `.bash_profile` or `.bashrc`,
add `/home/rtrottie/bin/VTST-Tools/` to your $PATH and $PYTHONPATH variables.

4. Load the `vasp_workflow` conda environment from `/home/rmorelock/.conda-envs/vasp_workflow`. On Eagle,
 execute `module load conda` to load Eagle's default conda environment. You can then run
 `conda activate /home/rmorelock/.conda-envs/vasp_workflow` to load the appropriate vasp_workflow environment.
 (Note: you may need to run `conda init bash` to make your default shell bash, thereby enabling the `conda activate` command.) You can also add `conda activate /home/rmorelock/.conda-envs/vasp_workflow` to an alias within your
`.bash_profile` or `.bashrc` for easier activation.

The `vasp_workflow` environment should have the following packages (among others):
* pymatgen
* pyyaml
* pycodestyle

You can check for these packages using the `conda list` command. You can also create your own environment and install these packages
with the following commands:
* `conda install -c conda-forge pymatgen`
* `conda install -c anaconda pyyaml`
* `conda install -c conda-forge pycodestyle`

**Note** I've had issues using Pymatgen's [MPRester](https://pymatgen.org/pymatgen.ext.matproj.html)
class in the `base` Eagle environment. For these reasons, try to use the
`/home/rmorelock/.conda-envs/vasp_workflow` environment if at all possible.

### Usage Requirements (Each Pull Request)

4. Navigate to the [configuration](https://github.com/rymo1354/vasp_workflow/tree/master/configuration) folder. In `config.py`, set the `MP_api_key` variable to your Material's Project API key. It's currently set to my personal MP API key. This will need
to be performed after each new pull request. Learn more at the Material's Project website
[link](https://materialsproject.org/open).

5. Run `python setup.py` in the `.../vasp_workflow` directory. This should make the
`rerun_workflow.py`, `generate_vasp_inputs.py`, `create_input_yaml.py` and
`vasp.py` scripts executable, if `.../vasp_workflow` and `.../vasp_workflow/workflow_scripts`
are on your path AND pythonpath.

You should be ready to go! If you're having issues with the setup, please contact me
at [myemail](mailto:rymo1354@colorado.edu).

## create_input_yaml.py

### Generating a .yml runfile

The first step for high-throughput calculations is the .yml runfile. This runfile
is generated using the `create_input_yaml.py` script. This script uses the `writeyaml.py`
module to generate the input .yml file. It takes three command line arguments:

* `-o` or `--outfile_name`: name of file to write to (with .yml extension) (Required)
* `-c` or `--copyfile_name`: name of file to copy (with .yml extension) (Optional)
* `-e` or `--edit_fields`: name of fields to edit (can choose multiple) (Optional)

If no `-c` tag is supplied, the `Default Inputs` dictionary from `.../configuration/yml_write_parameters.json`
is used. If `-c` is supplied, the new input dictionary is copied from a previously used dictionary. To
edit an existing dictionary, simply make the `-c` and `-o` tags the same.

The `-e` tag specifies which fields will be edited. Currently supported fields are:

* MPIDs
* PATHs
* Calculation_Type
* Relaxation_Set
* Magnetization_Scheme
* INCAR_Tags
* KPOINTs
* Max_Submissions

If no `-e` is supplied, all existing fields and tags will be copied to the `-c`
file path. Otherwise, the user will be prompted to modify the specified tags.

### MPIDs

Structures from the Material's Project can be used to get Vasp `POSCAR` files
by changing the `MPIDs` tag. The user is able to add or remove mp-ids; mp-ids that
are validated before they can be added to the .yml file. Example input for the
materials with the mp-id 'mp-5223' would be `mp-5223`.

### PATHs

Absolute paths of files on the computing system can also be used to get `POSCAR`
files. This files must be compatible with the `pymatgen.io.vasp.inputs.Poscar`
class to be read correctly, i.e. both valid Vasp `POSCAR` inputs and `CONTCAR`
outputs can be used. A more detailed description of how the `POSCAR` file is read
can be found on the Materials Project [website](https://pymatgen.org/pymatgen.io.vasp.inputs.html)

### Calculation_Type

Currently supported calculation `Type` are `bulk` and `defect`. Other arguments
include `Rescale` (automatic unit cell rescaling), as well as `Defect` for
`defect` calculations. `Defect` takes as an argument the abbreviated element on
which to perform the defect calculation (i.e. oxygen would be `O`).

### Relaxation_Set

Material's Project relaxation set used as the default for the calculation. Currently
supported sets include those listed in `MP Relaxation Sets` from
`.../configuration/yml_write_parameters.json`. More information about default
Material's Project relax sets can be found [here](https://pymatgen.org/pymatgen.io.vasp.sets.html).

### Magnetization_Scheme

Currently supported options for `Magnetization_Scheme` are `preserve`, `FM`, `AFM`
and `FM+AFM`. `preserve` maintains the original magnetism, `FM` performs a antiferromagnetic
enumeration, `AFM` performs an antiferromagnetic enumeration assuming the Material's Project
default magnetic spins, and `FM+AFM` does both a single ferromagnetic relaxation and
antiferromagnetic relaxations. Number of antiferromagnetic enumerations considered
should be specified if `AFM` or `FM+AFM` is chosen.

If a material is not magnetic and `FM`, `AFM` or `FM+AFM` is supplied as the scheme,
an alert will occur. The non-magnetized structure can still be generated, however.

### INCAR_Tags

Used to change the number of steps within a convergence calculation and the `INCAR`
tags at each step. Currently supported `INCAR_Tags` include those tags listed in the
`.../configuration/incar_parameters.json` file, as well as a few tags listed under
`VTST Tags` in `.../configuration/yml_write_parameters.json`.

These tags also allow for multi-step convergence schemes; currently supported step
can be found in the `.../configuration/yml_write_parameters.json` under
`Calculation_Steps`. Currently, steps `0 Step` through `10 Step` are supported.

**Note** User-supplied `INCAR_Tags` override existing tags already included by the
Materials Project relaxation set specified in the `Relaxation_Set` tag. Take special
care with the `LDAUU, LDAUJ and LDAUL` tags: certain Material's Project relax set
include these by default, and any user-supplied tags will overwrite all existing
`LDAUU, LDAUJ and LDAUL` tags. For more information visit the relaxation set
[link](https://pymatgen.org/pymatgen.io.vasp.sets.html).

### KPOINTs

Different `KPOINTs` tags for convergence steps can be supplied using the `KPOINTs`
tag. Only steps that have been specified in `INCAR_Tags` can have user-supplied `KPOINTs`.
`0 Step` tags have the option of all available KPOINT generation schemes as listed in
`.../configuration/yml_write_parameters.json` under `KPOINTS Generation`. All other
steps can only use `automatic_gamma_density` and `gamma_automatic`. This is due to
the multi-step convergence code used to submit and process multi-step jobs.

### Max_Submissions

Currently not supported in existing scripts. Will likely be used in a multi  
`Calculation_Type` workflow. This has not yet been implemented.  

## generate_vasp_inputs.py

### Generating the directory structure for VASP runs

The second step for high-throughput calculations is to use a .yml runfile to
generate the job submissions directory structure. This is performed with the
`generate_vasp_inputs.py` script. This script uses the `runfile_generation.py`
module. It takes a single command line argument:

* `-r` or `--readfile_path`: name of input .yml to read from (Required)

Navigate to the parent directory where you intend to generate the directories for
VASP runs. Run `generate_vasp_inputs.py -r </path/to/your_file.yml>`. Given a valid input .yml
file, the appropriate directory structure should be generated in the parent directory. Written
files should include valid `POSCAR`, `KPOINTS`, `INCAR` and `CONVERGENCE` files. With
the correct pseudopotentials in your `$PATH`, `POTCAR` files will also be written.

**Note** For best results, and unless you are familiar with this workflow, you should
use `create_input_yaml.py` for .yml generation. It has several checks to ensure that
the appropriate tags and their supported values are correctly input into the input
.yml file structure. Incorrect .yml files could disrupt file generation.

## rerun_workflow.py

### Submitting and re-running VASP jobs

If the above file structure was correctly generated, you are now ready to submit jobs.
Either a `bulk` or `defect` directory should have appeared in your parent directory. In
the parent directory, execute `rerun_workflow.py`. If jobs have not yet been submitted,
you will be prompted for a the name of this workflow. If jobs have already been submitted,
you will see the status of those jobs by rerunning `rerun_workflow.py`. Any failed jobs or
jobs that have reached their time limit will be stored in the directory system. To rerun these
jobs, simply execute `rerun_workflow.py`  

### Known Errors
If a job fails out of VASP because you didn't use the correct input parameters and/or VASP
compilation, custodian will report errors that do not make any sense. Use a simple bash
submission script to figure out the error. 
