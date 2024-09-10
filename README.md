
![Cover Image](image.jpg)

**Remote Manager** is a script designed for managing SSH connections and mounting remote file systems using `sshfs`.

## Dependencies

The script requires:

- Python >= 3.10
- Python libraries:
  - `paramiko`
  - `pyperclip`
  - `loguru`
  - `colorama`
- `sshfs` and `ssh` for mounting remote file systems

## Installation

### System Dependencies

Ensure that `sshfs`and `ssh` is installed for remote file system management:

1)Example (bash):
```
sudo apt-get update
sudo apt-get install -y sshfs
```

2)Clone repository and run `install.sh`


3)Export the Path to the Virtual Environment

After running the installation script, you'll need to ensure the virtual environment is properly activated when you use the script. If you followed the script, it should have automatically added the activation command to your .bashrc or .zshrc file.




