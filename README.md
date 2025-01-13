# python_serial_recorder

python-program to record data from a com-port


## Installation
Windows. For MacOS

1. Install python
   1. Option 1: download and use the installer from www.python.org
   2. Option 2: Use package manager. Pick the package manager you have installed on your system. If you dont have it, you can install one from their respective websites.  

   ```bash
   brew install python
   choco install python
   ```
      
2. Install new python environment (will avoid problems in the future)

    ```bash
    python -m ensurepip --default-pip
    python -m pip install --upgrade pip setuptools wheel
    python -m venv .venv

    ```
3. activate python environment
      1. MacOS
   
   ```bash
    source .venv/bin/activate  
   ```
      2. Windows
   
   ```bash
    source .venv/Scripts/activate  
   ```

4. install program requirements via reqirements.txt
   
    ```bash
    pip install -r requirements.txt
    ```


### how to install packages

If you do not know how to install new packages, I suggest reading the following page: https://packaging.python.org/en/latest/tutorials/installing-packages/

