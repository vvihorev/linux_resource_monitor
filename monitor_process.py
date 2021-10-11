import subprocess
import argparse
import os
import time


def _parse_top_stdout(proc):
    """
    Gets hardware usage statistics of a given process, using the 'top' command
    For UNIX systems only.
    Arguments:
        proc: subprocess.Popen() object
    Returns:
        A dictionary with hardware usage statistics of a process
    """
    stats = subprocess.run(['top', '-b', '-n', '2', '-d', '0.2', '-p',
                           str(proc.pid)], capture_output=True)
    stats = stats.stdout.decode('utf-8')

    res = []
    stats = stats.split('\n')[-3:-1]
    for stat in stats:
        stat = stat.split(' ')
        while ('' in stat):
            stat.remove('')
        res += stat

    statistics = {}
    for i in range(len(res) // 2):
        statistics[res[i]] = res[len(res) // 2 + i]
    return statistics


def get_cpu_and_memory(proc):
    """
    Gets CPU usage, Virtual Memory Size and Resident Set Size of a process
    VMS and RSS are in mb. Decimal digits are rounded.
    For UNIX systems only.
    Arguments:
        proc: subprocess.Popen() object
    Returns:
        An array with [VMS, RSS, CPU] as strings
    """
    stats = _parse_top_stdout(proc)
    vms = round(float(stats['VIRT']) / 1024)
    rss = round(float(stats['RES']) / 1024)
    cpu = round(float(stats['%CPU'].replace(',', '.')) / os.cpu_count())
    return [str(stat) for stat in [vms, rss, cpu]]


def get_fd_count(proc):
    """
    Gets number of active file descriptors for a process.
    For UNIX systems only.
    Arguments:
        proc: subprocess.Popen() object
    Returns:
        Number of active file descriptors
    """
    fd_location = '/proc/' + str(proc.pid) + '/fd'
    fd = subprocess.run(['ls', fd_location], capture_output=True)
    fd = fd.stdout.decode('utf-8')
    return len([n for n in fd.split('\n') if n != ''])


def get_cli_arguments():
    """
    Parses arguments passed to the script from the CLI.
    Returns:
        process: full path to the process or the process name
        interval: time interval between logs
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('process', type=str,
                        help='Path to the process to be logged')
    parser.add_argument('interval', type=float,
                        help='Time interval between logging in seconds')
    args = parser.parse_args()
    return args.process, args.interval


def log_statistics(proc, interval):
    """
    Starts logging of hardware usage for a process.
    Stops when the process is terminated.
    Has to be launched from a 'with open() as file:' loop.
    Arguments:
        proc: subprocess.Popen() object
        interval: time interval between logs in seconds
    """
    while proc.poll() == None:
        stats = []
        stats.append(str(time.asctime()))
        stats += get_cpu_and_memory(proc)
        stats.append(str(get_fd_count(proc)))

        file.write('\t'.join(stats))
        file.write('\n')

        time.sleep(interval - 0.2)


if __name__ == '__main__':
    # get arguments from the command line and start the process
    proc_name, interval = get_cli_arguments()
    proc = subprocess.Popen(proc_name)

    # create a dedicated filename for a process
    filename = proc_name.split('/')[-1] + '_log.tsv'

    # if the logfile already exists append to it, if not - create a new one
    if os.path.exists(filename):
        with open(filename, mode='a') as file:
            log_statistics(proc, interval)
    else:
        with open(filename, mode='a+') as file:
            column_names = '\t'.join(['TIME', 'VMS', 'RSS', '%CPU', 'FD'])
            file.write(column_names)
            file.write('\n')
            log_statistics(proc, interval)
    proc.terminate()

