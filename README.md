# python_serial_recorder

python-program to capture data from a com-port.
Included is an ardiono script for a esp32 to send data from a number of ports, to be specified in a list in the file `ADC_ttgo-t-display.ino`.

# Prereq

The code is build in vs code, and the guide to running the program is written here below

## Package-manager installation guides for windows and macos
Use the following guides to install a package manager if you do not already have one installed.

```zsh
- https://chocolatey.org/install
- https://brew.sh/
```

## git
- Install Git on your system. This is a way to download other peoples projects.

   ```bash
      brew install git
      choco install git
   ```

- Git gui: https://desktop.github.com/download/


## Python 

This program works with Python 3.13.2. However, it is very possible that it will also work with newer or older versions. I cannot garantee it however.

1. Option 1: download and use the installer from www.python.org
2. Option 2: Use package manager. Pick the package manager you have installed on your system. If you dont have it, you can install one from their respective websites.  
   - MacOS
   ```bash
      brew install python
   ```
   - Windows
   ```bash 
      choco install python
      
   ```

## how to install python packages via pip

If you do not know how to install new python packages using pip, I suggest reading the following page: https://packaging.python.org/en/latest/tutorials/installing-packages/


## Installation

For MacOS and Windows.

1. download git repository
   ```bash
   git clone https://github.com/nurrix/python_serial_recorder.git
   ```
      
2. Install new python environment (will avoid problems in the future)
   
    ```bash
    python -m ensurepip --default-pip
    python -m pip install --upgrade pip setuptools wheel
    python -m venv .venv
    ```
    
4. activate python environment
   - Depending on if it is not already activated when you open a terminal in VS Code, you can do the following.
     - MacOS

     ```bash
        source .venv/bin/activate  
     ```
     - Windows

     ```bash
        source .venv/Scripts/activate  
     ```

5. install program requirements via reqirements.txt
    ```bash
    pip install -r requirements.txt
    ```

# Run
The Python script is running the following code in the terminal, while inside the main python_serial_recorder folder.

```zsh
python main.py
```


