<img src="">

`____` aligns cell-stained images to the Allen Brain Atlas to allow for automatic brain region detection and excision with LEICA microdissection software. 

More information regarding the overall approach, methods and validations can be found in our publication:
<a href="">
<b>Title of paper</b>
Rishi Koneru, Manjari Anant^
</a>

## Overview

____ enables:
- alignment of cell stained slices to a 3D common coordinate framework
- automatic and manual annotaiton of brain regions
- excision of identified brain regions with LEICA software


## Installation & Import

### Installation using pip

This installation method is intended for users who sets up a Python environment without `pipenv`.

```
pip install --upgrade "git+https://github.com/JEFworks-Lab/STalign.git" <---- change this
```

*All dependencies will be installed into your selected environment with the above command. Dependencies can be found in the requirements.txt file.*

### Installation using Pipfile from source

This installation method is intended for users who sets up a Python environment with `pipenv`. `pipenv` allows users to create and activate a virtual environment with all dependencies within the Python project. For more information and installation instructions for `pipenv`, see https://pipenv.pypa.io/en/latest/.

Fork and `git clone` the `STalign` github repository.

From the base directory of your local `STalign` git repo, create a `Pipfile.lock` file from `Pipfile` using:

```
pipenv install requests
```

## Input Data
To use this tool, you will need provide the following information:

- 3D Reference Atlas with cell stain and region annotations(not needed if using Allen Brain Atlas)
- Cell stained images from LEICA LDM on slides 

## Usage

To use `____`, please refer to our [tutorials](https://jef.works/STalign/tutorials.html).

