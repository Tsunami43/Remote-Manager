
import argparse
import paramiko
import os
import sys
import json
import subprocess
import signal
from loguru import logger
from colorama import Fore, Style, init
import pyperclip

init()

title = f"""{Fore.MAGENTA}
██████╗░███████╗███╗░░░███╗░█████╗░████████╗███████╗
██╔══██╗██╔════╝████╗░████║██╔══██╗╚══██╔══╝██╔════╝
██████╔╝█████╗░░██╔████╔██║██║░░██║░░░██║░░░█████╗░░
██╔══██╗██╔══╝░░██║╚██╔╝██║██║░░██║░░░██║░░░██╔══╝░░
██║░░██║███████╗██║░╚═╝░██║╚█████╔╝░░░██║░░░███████╗
╚═╝░░╚═╝╚══════╝╚═╝░░░░░╚═╝░╚════╝░░░░╚═╝░░░╚══════╝

███╗░░░███╗░█████╗░███╗░░██╗░█████╗░░██████╗░███████╗██████╗░
████╗░████║██╔══██╗████╗░██║██╔══██╗██╔════╝░██╔════╝██╔══██╗
██╔████╔██║███████║██╔██╗██║███████║██║░░██╗░█████╗░░██████╔╝
██║╚██╔╝██║██╔══██║██║╚████║██╔══██║██║░░╚██╗██╔══╝░░██╔══██╗
██║░╚═╝░██║██║░░██║██║░╚███║██║░░██║╚██████╔╝███████╗██║░░██║
╚═╝░░░░░╚═╝╚═╝░░╚═╝╚═╝░░╚══╝╚═╝░░╚═╝░╚═════╝░╚══════╝╚═╝░░╚═╝
{Style.RESET_ALL}"""

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) + '/'
NEW_MOUNTED_DIR = CURRENT_DIR + "mnt/"
CONNECTIONS_FILE = CURRENT_DIR + '.connections.json'
DEFAULT_SSH_KEY_PATH = os.path.expanduser('~/.ssh/id_rsa')

logger.remove()
logger.add(sys.stdout, level="INFO", format="{message}")


class SSHConnectionManager:
    def __init__(self):
        self.connections = self.load_connections()

    def load_connections(self):
        if os.path.exists(CONNECTIONS_FILE):
            try:
                with open(CONNECTIONS_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Error loading connections from JSON: {e}")
                return {}
            except Exception as e:
                logger.error(f"Unexpected error loading connections: {e}")
                return {}
        return {}

    def save_connection(self, name, login, address, password):
        self.connections[name] = {
            'login': login,
            'address': address,
            'password': password
        }
        try:
            with open(CONNECTIONS_FILE, 'w') as f:
                json.dump(self.connections, f, indent=4)
            logger.info(f"{Fore.GREEN}Connection {name} saved successfully.{Style.RESET_ALL}")
        except IOError as e:
            logger.error(f"Error saving connection to JSON: {e}")

    def list_connections(self, hide=True):
        if self.connections:
            for name, details in self.connections.items():
                login = details['login']
                address = details['address']
                password = details['password']
                logger.info(f"{Fore.CYAN}{name}:{Style.RESET_ALL}\n"
                            f"\t{Fore.GREEN}Host: {login}@{address}\n"
                            f"\t{Fore.RED}Password: { '[hidden]' if not hide else password}{Style.RESET_ALL}\n")
        else:
            logger.info(f"{Fore.YELLOW}No connections found.{Style.RESET_ALL}")

    def check_ssh_connection(self, login, address, password):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(address, username=login, password=password, timeout=10)
            client.close()
            logger.info(f"{Fore.GREEN}Successfully connected to {address} as {login}.{Style.RESET_ALL}")
            return True
        except Exception as e:
            logger.error(f"{Fore.RED}Error connecting to SSH: {e}{Style.RESET_ALL}")
            return False

    def send_ssh_key(self, login, address, password, ssh_key=DEFAULT_SSH_KEY_PATH):
        if not os.path.exists(ssh_key):
            logger.error(f"SSH key not found at {ssh_key}")
            return False
        pyperclip.copy(password)
        try:
            logger.info(f"{Fore.CYAN}Sending SSH key to {login}@{address}{Style.RESET_ALL}")

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(address, username=login, password=password, timeout=10)

            commands = [
                'mkdir -p ~/.ssh',
                'chmod 700 ~/.ssh',
                'touch ~/.ssh/authorized_keys',
                'chmod 600 ~/.ssh/authorized_keys'
            ]
            for command in commands:
                stdin, stdout, stderr = client.exec_command(command)
                stdout.channel.recv_exit_status()
                error = stderr.read().decode().strip()
                if error:
                    logger.error(f"Error executing command '{command}': {error}")

            sftp = client.open_sftp()
            sftp.put(ssh_key, '/tmp/id_rsa.pub')
            sftp.close()

            command = (
                'cat /tmp/id_rsa.pub >> ~/.ssh/authorized_keys && '
                'chmod 600 ~/.ssh/authorized_keys && '
                'rm /tmp/id_rsa.pub'
            )
            stdin, stdout, stderr = client.exec_command(command)
            stdout.channel.recv_exit_status()
            error = stderr.read().decode().strip()
            if error:
                logger.error(f"Error executing command '{command}': {error}")

            client.close()
            logger.info(f"SSH key successfully added to {login}@{address}")
            return True
        except Exception as e:
            logger.error(f"Error sending SSH key: {e}")
            return False


class MountManager:
    def mount_connection(self, login, password, address, name):
        mount_point = f"{NEW_MOUNTED_DIR}{name}"
        pyperclip.copy(password)

        if not os.path.exists(mount_point):
            try:
                logger.info(f"{Fore.CYAN}Creating mount point {mount_point}{Style.RESET_ALL}")
                os.makedirs(mount_point)
            except PermissionError:
                logger.error(f"{Fore.RED}Permission denied: unable to create {mount_point}. Try running with sudo.{Style.RESET_ALL}")
                sys.exit(1)
            except Exception as e:
                logger.error(f"Error creating mount point: {e}")
                sys.exit(1)

        ssh_key = os.path.expanduser("~/.ssh/id_rsa") #,IdentityFile={ssh_key}
        logger.info(f"{Fore.CYAN}Mounting {name} at {mount_point}{Style.RESET_ALL}")
        try:
            result = subprocess.run(['sudo', 'sshfs', '-o', f'allow_other', f'{login}@{address}:', mount_point], check=True)
            logger.info(f"{Fore.GREEN}Mounting completed.{Style.RESET_ALL}")
        except subprocess.CalledProcessError as e:
            logger.error(f"{Fore.RED}Failed to mount {name} at {mount_point}: {e}{Style.RESET_ALL}")
            sys.exit(1)


    def unmount_connection(self, name):
        mount_point = f"{NEW_MOUNTED_DIR}{name}"
        if os.path.ismount(mount_point):
            logger.info(f"{Fore.CYAN}Unmounting {name} from {mount_point}{Style.RESET_ALL}")
            try:
                subprocess.run(['sudo', 'fusermount', '-u', mount_point], check=True)
                logger.info(f"{Fore.GREEN}Unmounting completed.{Style.RESET_ALL}")
            except subprocess.CalledProcessError as e:
                logger.error(f"{Fore.RED}Failed to unmount {name}: {e}{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"Error during unmounting: {e}")
        else:
            logger.info(f"{Fore.YELLOW}Mount point does not exist or is not mounted.{Style.RESET_ALL}")




def print_help():
    help_text = """
Usage: remote <command> [options]

Commands:
  new         Create a new SSH connection
  conn        Connect to an existing SSH connection
  list        List all saved SSH connections
  mount       Mount a remote file system via sshfs
  send-key    Send an SSH key to a remote server
  unmount     Unmount a previously mounted file system

Options:
  -h, --help   Show this help message and exit
  name         Name of the connection
  ssh_key      Path to SSH key for send-key command
  mount_point  Mount point for sshfs
  --no-hide    Show passwords in the list (by default, passwords are hidden)
  """
    logger.info(help_text)


def main():
    parser = argparse.ArgumentParser(description='Manage SSH connections.', prog='remote')
    parser.add_argument('command', nargs='?', help='Command to execute')
    parser.add_argument('name', nargs='?', help='Name of the connection')
    parser.add_argument('ssh_key', nargs='?', help='Path to SSH key for send-key command')
    parser.add_argument('mount_point', nargs='?', help='Mount point for sshfs')
    parser.add_argument('--no-hide', action='store_true', help='Show passwords in the list')

    args = parser.parse_args()

    ssh_manager = SSHConnectionManager()
    mount_manager = MountManager()

    if not args.command:
        print(title)
        return

    if args.command == 'new':
        if args.name in ssh_manager.connections or args.name is None:
            logger.error(f"{Fore.RED}Connection name already exists.{Style.RESET_ALL}")
            sys.exit(1)

        login = input('Enter SSH login: ')
        address = input('Enter SSH address: ')
        password = input('Enter SSH password: ')

        if ssh_manager.check_ssh_connection(login, address, password):
            ssh_manager.save_connection(args.name, login, address, password)

            send_key_choice = input('Do you want to send the SSH key to the server? (yes/no): ').strip().lower()
            if send_key_choice == 'yes':
                ssh_key_path = args.ssh_key if args.ssh_key else DEFAULT_SSH_KEY_PATH
                if ssh_manager.send_ssh_key(login, address, password, ssh_key_path):
                    logger.info(f"{Fore.GREEN}SSH key sent and connection saved successfully.{Style.RESET_ALL}")
                else:
                    logger.error(f"{Fore.RED}Failed to send SSH key, but connection was saved.{Style.RESET_ALL}")
            sys.exit(0)
        else:
            sys.exit(1)

    elif args.command == 'conn':
        if args.name in ssh_manager.connections:
            login, address, password = ssh_manager.connections[args.name].values()
            pyperclip.copy(password)
            logger.info(f"{Fore.CYAN}Connecting to {args.name}: {login}@{address}{Style.RESET_ALL}")
            os.system(f'ssh {login}@{address}')
            logger.info(f"{Fore.GREEN}Connection closed.{Style.RESET_ALL}")
            sys.exit(0)
        else:
            logger.error(f"{Fore.RED}Connection not found.{Style.RESET_ALL}")
            sys.exit(1)

    elif args.command == 'list':
        ssh_manager.list_connections(args.no_hide)
        sys.exit(0)

    elif args.command == 'mount':
        if args.name in ssh_manager.connections:
            login, address, password = ssh_manager.connections[args.name].values()
            mount_manager.mount_connection(login, password, address, args.name)
        else:
            logger.error(f"{Fore.RED}Connection not found.{Style.RESET_ALL}")
            sys.exit(1)

    elif args.command == 'send-key':
        if args.name in ssh_manager.connections:
            login, address, password = ssh_manager.connections[args.name].values()
            ssh_key_path = args.ssh_key if args.ssh_key else DEFAULT_SSH_KEY_PATH
            ssh_manager.send_ssh_key(login, address, password, ssh_key_path)
        else:
            logger.error(f"{Fore.RED}Connection not found.{Style.RESET_ALL}")
            sys.exit(1)

    elif args.command == 'unmount':
        if args.name:
            mount_manager.unmount_connection(args.name)
        else:
            logger.error(f"{Fore.RED}No mount point specified for unmount.{Style.RESET_ALL}")
            sys.exit(1)

    else:
        logger.error(f"{Fore.RED}Command not found.{Style.RESET_ALL}")
        print_help()
        sys.exit()


if __name__ == '__main__':
    main()

