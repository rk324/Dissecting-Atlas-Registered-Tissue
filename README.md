## Overview

Dissecting Atlas-Registered Tissue (DART) aligns cell-stained images to the Allen Brain Atlas to allow for automatic brain region detection and excision with LEICA laser microdissection software. 

DART enables:
- Automated or semi-automated alignment of 2D brain slices to a 3D atlas (e.g., the Allen Brain Atlas CCFv3 2017) and atlas-based segmentation. 
- Automatic generation of ROI boundaries.
- Seamless sample handling and integration with Leica LMD software for laser dissection. 

<figure>
    <img src=DART_alignment_results.png alt="DART Alignment Results">
    <figcaption>
        DART alignment results on various brain sections</>
    </figcaption>
</figure>

## Installation

DART can currently be installed via two methods: 
1. [downloading the pre-compiled Windows binary](#executable-file)
2. [cloning the github repository and downloading auxiliary files](#cloning-this-repository)

Regardless of installation method, DART is available only on Windows 11. It was tested on a computer with 192 GB RAM and 24 GB graphics card. Running DART on less powerful devices may cause issues with loading high-resolution atlases and significantly slow processing time. 

### Executable File
DART is available as a pre-compiled Windows binary in a standalone folder that includes all necessary dependencies. This installation method is perfect for users with little or no coding experience. To use the software, download and extract the entire folder from the [Google Drive link](https://drive.google.com/file/d/1UHvkmNt6kgneh7vLTZS29K53wJkYFOEJ/view?usp=sharing), then run the `main.exe` file inside—no installation or separate Python environment is required.

### Cloning this repository
DART can also be installed by cloning the repository and downloading auxiliary files. This is ideal for editing or contributing to the software and is necessary for running unit tests via pytest. To succesfully install DART with this method follow these steps:

1. Clone this repository using `git clone https://github.com/rk324/Dissecting-Atlas-Registered-Tissue.git`
2. Set up a conda environment by navigating into the repository folder and using `conda env create -f environment.yml`
3. From the repository folder, download the atlases using `python -m dart.download_atlases`
    - Alternatively, the atlases can be manually downloaded and extracted from the [Zenodo archive](https://zenodo.org/records/17849564). These atlases should be extracted to the folder `dart/dart/atlases`.
    - Note: The `atlases` folder should have 5 subfolders, and each of those should have 3 subfiles titled `label.nrrd`, `reference.nrrd`, and `names_dict.csv`.
4. To run the software as a user, call `python -m dart` from the root directory of the repository.

Installing DART via repository cloning enables several additional tools for developers:
1. The automated tests can be run with pytest using either `pytest --disable-warnings` or `python -m pytest --disable-warnings`.
2. Individual pages can be "demoed" by calling `python -m dart.demo` from the root directory of the repository. This opens up a GUI where users can select a specific page and view it without needing to proceed through the previous pages.

## Input Data
To use this tool, you will need provide the following information:

- 3D Reference Atlas with cell stain and region annotations (included in installation if using Allen Brain Atlas)
- A folder containing cell stained images from LEICA LDM on slides 

## Usage

To use `DART`, please refer to our [tutorial](tutorials/README.md).

## License
- DART's source code is available under the GNU General Public License version 3
- VisuAlign is developed by the Neural Systems Laboratory at the Institute of Basic Medical Sciences, University of Oslo, Norway and is licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 License](https://creativecommons.org/licenses/by-nc-sa/4.0/)

## Contributing
For support or issues, please open an “Issue” on our GitHub repository. To contribute to the software, please refer to our [Contribution guidelines](CONTRIBUTING.md)


