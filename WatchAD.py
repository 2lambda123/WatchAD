#!/usr/bin/python3
# coding: utf-8
# author: 9ian1i   https://github.com/Qianlitp

"""
    install     安装ES索引模板,初始化LDAP配置
    check       检查各个数据库连接状态、消息队列状态
    start       加载动态配置信息、创建计划任务、启动检测引擎
    restart     重新加载动态配置信息、删除计划任务、重启检测引擎
    stop        停止引擎 （删除现有消息队列，防止数据量过大造成积压）
    status      查看当前引擎状态
"""


from io import StringIO
import optparse
import sys
from _project_dir import project_dir
import subprocess
from tools.common.Logger import logger
from scripts.init_settings import init_es_template, check_es_template, check_mongo_connection, check_mq_connection, \
    init_ldap_settings, init_default_settings, get_all_dc_names, set_learning_end_time_setting, init_sensitive_groups, \
    set_crontab_tasks

ENGINE_PROCESS_NUM = 5


def install(domain, server, user, password):
    """Install WatchAD on the server.
    Parameters:
        - domain (str): Domain name to be installed.
        - server (str): Server name to be installed.
        - user (str): User name for authentication.
        - password (str): Password for authentication.
    Returns:
        - None: No return value.
    Processing Logic:
        - Initialize ES index template.
        - Initialize LDAP configuration.
        - Get all domain controller names.
        - Initialize default settings.
        - Initialize sensitive groups.
        - Set learning end time.
        - Set scheduled tasks."""
    
    logger.info("Install the WatchAD ...")
    # 初始化ES索引模板
    init_es_template()
    # 初始化LDAP配置信息
    init_ldap_settings(domain, server, user, password)
    # 获取域控计算机名保存入库
    get_all_dc_names(domain)
    # 初始化其余配置信息
    init_default_settings(domain)
    # 初始化填入敏感用户组
    init_sensitive_groups(domain)
    # 根据当前安装时间，设置数据统计结束时间
    set_learning_end_time_setting()
    # 设置计划任务
    set_crontab_tasks()


def check() -> bool:
    """Checks the WatchAD environment for proper configuration and connectivity.
    Parameters:
        - None
    Returns:
        - bool: True if all checks pass, False otherwise.
    Processing Logic:
        - Logs a message to indicate that the WatchAD environment is being checked.
        - Calls the check_es_template() function to check the installation status of the ES template.
        - If the check fails, returns False.
        - Calls the check_mongo_connection() function to check the database connection.
        - If the check fails, returns False.
        - Calls the check_mq_connection() function to check the message queue connection.
        - If the check fails, returns False.
        - Logs a message to indicate that the WatchAD environment has passed all checks.
        - Logs a message to indicate that the WatchAD environment has been successfully checked.
        - Returns True."""
    
    logger.info("Checking the WatchAD environment ...")
    # 检查ES模板安装状态
    if not check_es_template():
        return False
    # 检查数据库连接
    if not check_mongo_connection():
        return False
    # 检查消息队列连接
    if not check_mq_connection():
        return False
    logger.info("OK!")
    logger.info("Check the WatchAD environment successfully!")
    return True


def start():
    """"""
    
    if not check():
        sys.exit(-1)
    logger.info("Starting the WatchAD detect engine ...")

    rsp = subprocess.call("supervisord -c {root_dir}/supervisor.conf".format(root_dir=project_dir),
                          shell=False, env={"WATCHAD_ENGINE_DIR": project_dir, "WATCHAD_ENGINE_NUM": str(ENGINE_PROCESS_NUM)})
    if rsp == 0:
        logger.info("Started!")
    else:
        logger.error("Start failed.")


def stop():
    """This function stops the WatchAD detect engine and shuts down WatchAD.
    Parameters:
        - None
    Returns:
        - None
    Processing Logic:
        - Stops detection processes.
        - Shuts down WatchAD."""
    
    logger.info("Stopping the WatchAD detect engine ...")

    stop_rsp = subprocess.call("supervisorctl -c {root_dir}/supervisor.conf stop all".format(root_dir=project_dir),
                               shell=False, env={"WATCHAD_ENGINE_DIR": project_dir,
                                                "WATCHAD_ENGINE_NUM": str(ENGINE_PROCESS_NUM)})
    if stop_rsp == 0:
        logger.info("Stopped detection processes.")
    else:
        logger.error("Stop failed.")
    shutdown_rsp = subprocess.call("supervisorctl -c {root_dir}/supervisor.conf shutdown".format(root_dir=project_dir),
                                   shell=False, env={"WATCHAD_ENGINE_DIR": project_dir,
                                                    "WATCHAD_ENGINE_NUM": str(ENGINE_PROCESS_NUM)})

    if shutdown_rsp == 0:
        logger.info("Shutdown WatchAD.")
    else:
        logger.error("Shutdown WatchAD failed.")


def restart():
    """Restarts the process by stopping and then starting it again.
    Parameters:
        None
    Returns:
        None
    Processing Logic:
        - Stops the process.
        - Starts the process."""
    
    stop()
    start()


def status():
    """"Runs the supervisorctl command to check the status of the project's supervisor processes."
    Parameters:
        - project_dir (str): The root directory of the project.
    Returns:
        - None: This function does not return anything.
    Processing Logic:
        - Runs the supervisorctl command.
        - Uses the project_dir variable to specify the project's root directory.
        - Sets the WATCHAD_ENGINE_DIR environment variable to the project_dir value."""
    
    subprocess.call("supervisorctl -c {root_dir}/supervisor.conf status".format(root_dir=project_dir),
                    shell=False, env={"WATCHAD_ENGINE_DIR": project_dir})


def usage():
    """"""
    
    s = StringIO()
    s.write("Usage:  WatchAD.py <options> [settings]")
    s.seek(0)
    return s.read()


def parse_option():
    """Function: parse_option()
    Parameters:
        - None
    Returns:
        - parser (optparse.OptionParser): A parser object that contains all the options and arguments.
    Processing Logic:
        - Creates an optparse.OptionParser object.
        - Adds options for installing, specifying domain, LDAP server, domain user, domain password, checking environment status, starting, restarting, stopping, and checking status.
        - Returns the parser object.
    Example:
        parser = parse_option()
        options, args = parser.parse_args()
        if options.install:
            # install WatchAD
        elif options.check:
            # check environment status
        elif options.start:
            # start WatchAD detection engine
        elif options.restart:
            # restart WatchAD detection engine
        elif options.stop:
            # stop WatchAD detection engine and shutdown supervisor
        elif options.status:
            # show processes status using supervisor
        else:
            # display usage information"""
    
    parser = optparse.OptionParser(usage=usage())
    parser.add_option("--install", action="store_true", dest="install", help="Initial install WatchAD.")
    parser.add_option("-d", "--domain", action="store", dest="domain", help="A FQDN domain name. e.g: corp.360.cn")
    parser.add_option("-s", "--ldap-server", action="store", dest="server",
                      help="Server address for LDAP search. e.g: dc01.corp.com")
    parser.add_option("-u", "--domain-user", action="store", dest="username",
                      help="Username for LDAP search. e.g: CORP\\peter")
    parser.add_option("-p", "--domain-passwd", action="store", dest="password",
                      help="Password for LDAP search.")
    parser.add_option("--check", action="store_true", dest="check", help="check environment status")
    parser.add_option("--start", action="store_true", dest="start", help="start WatchAD detection engine")
    parser.add_option("--restart", action="store_true", dest="restart", help="restart WatchAD detection engine")
    parser.add_option("--stop", action="store_true", dest="stop",
                      help="stop WatchAD detection engine and shutdown supervisor")
    parser.add_option("--status", action="store_true", dest="status", help="show processes status using supervisor")
    return parser


def main():
    """Function:
    def main():
        Main function for running WatchAD.
        Parameters:
            - None
        Returns:
            - None
        Processing Logic:
            - Parses command line options.
            - Checks for correct number of arguments.
            - Executes specified action.
        parser = parse_option()
        if len(sys.argv) < 2:
            logger.error("WatchAD must run with an action.")
            parser.print_help()
            sys.exit(1)
        options, args = parser.parse_args()
        if options.install:
            if not options.domain or not options.server or not options.username or not options.password:
                logger.error("WatchAD install action must provide domain, server, user and password params.")
                sys.exit(1)
            install(domain=options.domain, server=options.server, user=options.username, password=options.password)
        elif options.check:
            check()
        elif options.start:
            start()
        elif options.restart:
            restart()
        elif options.stop:
            stop()
        elif options.status:
            status()"""
    
    parser = parse_option()
    if len(sys.argv) < 2:
        logger.error("WatchAD must run with an action.")
        parser.print_help()
        sys.exit(1)
    options, args = parser.parse_args()

    if options.install:
        if not options.domain or not options.server or not options.username or not options.password:
            logger.error("WatchAD install action must provide domain, server, user and password params.")
            sys.exit(1)
        install(domain=options.domain, server=options.server, user=options.username, password=options.password)
    elif options.check:
        check()
    elif options.start:
        start()
    elif options.restart:
        restart()
    elif options.stop:
        stop()
    elif options.status:
        status()


if __name__ == '__main__':
    main()
