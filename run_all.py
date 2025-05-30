import subprocess
import time
import sys
from pyfiglet import Figlet
from colorama import init, Fore, Style

init(autoreset=True)

def print_banner(text, color_enabled=True):
    fig = Figlet(font='slant')
    banner = fig.renderText(text.upper())
    if color_enabled:
        print(Fore.CYAN + banner + Style.RESET_ALL)
    else:
        print(banner)

def main():
    # Toggle this flag to enable/disable colors
    use_color = True

    # Get algorithm name from command-line argument
    if len(sys.argv) < 2:
        print("Usage: python run_all.py [lamport|agrawala]")
        sys.exit(1)

    algorithm = sys.argv[1].lower()

    # Map algorithm name to script
    if algorithm == "lamport":
        script_name = "lamport_mutex.py"
        algorithm_display = "LAMPORT"
    elif algorithm == "agrawala":
        script_name = "ricart_agrawala_mutex.py"
        algorithm_display = "AGRAWALA"
    else:
        print("Unknown algorithm. Use 'lamport' or 'agrawala'.")
        sys.exit(1)

    # Print the banner
    print_banner(algorithm_display, color_enabled=use_color)

    # Define commands for the three processes
    cmds = [
        ["python", script_name, "--pid", "1", "--port", "50051", "--peers", "1:localhost:50051,2:localhost:50052,3:localhost:50053"],
        ["python", script_name, "--pid", "2", "--port", "50052", "--peers", "1:localhost:50051,2:localhost:50052,3:localhost:50053"],
        ["python", script_name, "--pid", "3", "--port", "50053", "--peers", "1:localhost:50051,2:localhost:50052,3:localhost:50053"],
    ]

    procs = [subprocess.Popen(cmd) for cmd in cmds]

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTerminating processes...")
        for p in procs:
            p.terminate()

if __name__ == "__main__":
    main()
