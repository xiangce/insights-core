"""
This module defines all datasources used by standard Red Hat Insight components.

To define data sources that override the components in this file, create a
`insights.core.spec_factory.SpecFactory` with "insights.specs" as the constructor
argument. Data sources created with that factory will override components in
this file with the same `name` keyword argument. This allows overriding the
data sources that standard Insights `Parsers` resolve against.
"""

import logging
import signal

# TODO: When adding new importing, Please
# - keep the modules in sort of alphabet
# - keep line length less than 80 characters
from insights.components.ceph import IsCephMonitor
from insights.components.cloud_provider import IsAzure, IsGCP
from insights.components.rhel_version import IsGtOrRhel84, IsGtOrRhel86
from insights.components.satellite import (
    IsSatellite,
    IsSatellite611,
    IsSatellite614AndLater,
    IsSatelliteLessThan614,
)
from insights.components.selinux import SELinuxEnabled
from insights.components.virtualization import IsBareMetal
from insights.core.context import HostContext
from insights.core.spec_factory import (
    RawFileProvider,
    command_with_args,
    container_collect,
    container_execute,
    first_file,
    first_of,
    foreach_collect,
    foreach_execute,
    glob_file,
    head,
    listdir,
    simple_command,
    simple_file,
)
from insights.specs import Specs
from insights.specs.datasources import (
    aws,
    awx_manage,
    client_metadata,
    cloud_init,
    corosync as corosync_ds,
    db2,
    dev,
    du,
    eap_reports,
    env,
    ethernet,
    httpd,
    intersystems,
    ipcs,
    kernel,
    leapp,
    lpstat,
    ls,
    lsattr,
    luks,
    machine_id,
    md5chk,
    mdadm,
    mount as mount_ds,
    package_provides,
    ps,
    rpm,
    sap,
    satellite,
    ssl_certificate,
    sys_fs_cgroup_memory,
    user_group,
    yum_updates,
)
from insights.specs.datasources.compliance import compliance_ds
from insights.specs.datasources.container import containers_inspect, running_rhel_containers
from insights.specs.datasources.container.nginx_conf import nginx_conf as container_nginx_conf_ds
from insights.specs.datasources.malware_detection import malware_detection_ds
from insights.specs.datasources.pcp import (
    pcp_enabled,
    pcp_raw_files,
    pmlog_summary_args,
    pmlog_summary_args_pcp_zeroconf,
)
from insights.specs.datasources.rpm import _rpm_format
from insights.specs.datasources.sap import sap_hana_sid, sap_hana_sid_SID_nr

logger = logging.getLogger(__name__)


class DefaultSpecs(Specs):
    # Dependent specs that aren't in the registry
    block_devices_by_uuid = listdir("/dev/disk/by-uuid/", context=HostContext)
    httpd_pid = simple_command("/usr/bin/pgrep -o httpd")
    openshift_router_pid = simple_command("/usr/bin/pgrep -n openshift-route")
    ovs_vsctl_list_br = simple_command("/usr/bin/ovs-vsctl list-br")

    # Client metadata specs/files
    ansible_host = client_metadata.ansible_host
    blacklist_report = client_metadata.blacklist_report
    blacklisted_specs = client_metadata.blacklisted_specs
    branch_info = client_metadata.branch_info
    display_name = client_metadata.display_name
    egg_release = client_metadata.egg_release
    tags = client_metadata.tags
    version_info = client_metadata.version_info

    # Client App specs
    compliance = compliance_ds.compliance
    compliance_policies = compliance_ds.compliance_policies
    compliance_assign = compliance_ds.compliance_assign
    compliance_unassign = compliance_ds.compliance_unassign
    malware_detection = malware_detection_ds.malware_detection

    # Regular collection specs
    abrt_ccpp_conf = simple_file("/etc/abrt/plugins/CCpp.conf")
    abrt_status_bare = simple_command("/usr/bin/abrt status --bare=True")
    alternatives_display_python = simple_command("/usr/sbin/alternatives --display python")
    amq_broker = glob_file("/var/opt/amq-broker/*/etc/broker.xml")
    audit_log = simple_file("/var/log/audit/audit.log")
    auditctl_rules = simple_command("/sbin/auditctl -l")
    auditctl_status = simple_command("/sbin/auditctl -s")
    auditd_conf = simple_file("/etc/audit/auditd.conf")
    audispd_conf = simple_file("/etc/audisp/audispd.conf")
    ausearch_insights = simple_command(
        "/usr/sbin/ausearch -i -m avc,user_avc,selinux_err,user_selinux_err -ts recent",
        deps=[IsGtOrRhel86],
        keep_rc=True,
    )
    aws_instance_id_doc = command_with_args(
        '/usr/bin/curl -s -H "X-aws-ec2-metadata-token: %s" http://169.254.169.254/latest/dynamic/instance-identity/document --connect-timeout 5',
        aws.aws_imdsv2_token,
        deps=[aws.aws_imdsv2_token],
    )
    aws_instance_id_pkcs7 = command_with_args(
        '/usr/bin/curl -s -H "X-aws-ec2-metadata-token: %s" http://169.254.169.254/latest/dynamic/instance-identity/pkcs7 --connect-timeout 5',
        aws.aws_imdsv2_token,
        deps=[aws.aws_imdsv2_token],
    )
    aws_public_hostnames = command_with_args(
        '/usr/bin/curl -s -H "X-aws-ec2-metadata-token: %s" http://169.254.169.254/latest/meta-data/public-hostname --connect-timeout 5',
        aws.aws_imdsv2_token,
        deps=[aws.aws_imdsv2_token],
    )
    aws_public_ipv4_addresses = command_with_args(
        '/usr/bin/curl -s -H "X-aws-ec2-metadata-token: %s" http://169.254.169.254/latest/meta-data/public-ipv4 --connect-timeout 5',
        aws.aws_imdsv2_token,
        deps=[aws.aws_imdsv2_token],
    )
    awx_manage_check_license = simple_command("/usr/bin/awx-manage check_license")
    awx_manage_check_license_data = awx_manage.check_license_data
    awx_manage_print_settings = simple_command(
        "/usr/bin/awx-manage print_settings INSIGHTS_TRACKING_STATE SYSTEM_UUID INSTALL_UUID TOWER_URL_BASE AWX_CLEANUP_PATHS AWX_PROOT_BASE_PATH LOG_AGGREGATOR_ENABLED LOG_AGGREGATOR_LEVEL --format json"
    )
    azure_instance_id = simple_command(
        "/usr/bin/curl -s -H Metadata:true http://169.254.169.254/metadata/instance/compute/vmId?api-version=2021-12-13&format=text --connect-timeout 5",
        deps=[IsAzure],
    )
    azure_instance_plan = simple_command(
        "/usr/bin/curl -s -H Metadata:true http://169.254.169.254/metadata/instance/compute/plan?api-version=2021-12-13&format=json --connect-timeout 5",
        deps=[IsAzure],
    )
    azure_instance_type = simple_command(
        "/usr/bin/curl -s -H Metadata:true http://169.254.169.254/metadata/instance/compute/vmSize?api-version=2021-12-13&format=text --connect-timeout 5",
        deps=[IsAzure],
    )
    azure_load_balancer = simple_command(
        "/usr/bin/curl -s -H Metadata:true http://169.254.169.254/metadata/loadbalancer?api-version=2021-12-13&format=json --connect-timeout 5",
        deps=[IsAzure],
    )
    basic_auth_insights_client = client_metadata.basic_auth_insights_client
    bdi_read_ahead_kb = glob_file("/sys/class/bdi/*/read_ahead_kb")
    blkid = simple_command("/sbin/blkid -c /dev/null")
    bond = glob_file("/proc/net/bonding/*")
    bond_dynamic_lb = glob_file("/sys/class/net/*/bonding/tlb_dynamic_lb")
    boot_loader_entries = glob_file("/boot/loader/entries/*.conf")
    bootc_status = simple_command("/usr/bin/bootc status --json")
    buddyinfo = simple_file("/proc/buddyinfo")
    brctl_show = simple_command("/usr/sbin/brctl show")
    candlepin_log = simple_file("/var/log/candlepin/candlepin.log")
    cciss = glob_file("/proc/driver/cciss/cciss*")
    cdc_wdm = simple_file("/sys/bus/usb/drivers/cdc_wdm/module/refcnt")
    ceph_conf = first_file(
        ["/var/lib/config-data/puppet-generated/ceph/etc/ceph/ceph.conf", "/etc/ceph/ceph.conf"]
    )
    ceph_health_detail = simple_command("/usr/bin/ceph health detail -f json")
    ceph_insights = simple_command("/usr/bin/ceph insights", deps=[IsCephMonitor])
    ceph_osd_dump = simple_command("/usr/bin/ceph osd dump -f json")
    ceph_osd_tree = simple_command("/usr/bin/ceph osd tree -f json")
    ceph_v = simple_command("/usr/bin/ceph -v")
    certificates_enddate = simple_command(
        r"/usr/bin/find /etc/origin/node /etc/origin/master /etc/pki /etc/ipa /etc/tower/tower.cert -type f -exec /usr/bin/openssl x509 -noout -enddate -in '{}' \; -exec echo 'FileName= {}' \;",
        keep_rc=True,
    )
    cgroups = simple_file("/proc/cgroups")
    chrony_conf = simple_file("/etc/chrony.conf")
    chronyc_sources = simple_command("/usr/bin/chronyc sources")
    cib_xml = simple_file("/var/lib/pacemaker/cib/cib.xml")
    cifs_debug_data = simple_file("/proc/fs/cifs/DebugData")
    cinder_conf = first_file(
        [
            "/var/lib/config-data/puppet-generated/cinder/etc/cinder/cinder.conf",
            "/etc/cinder/cinder.conf",
        ]
    )
    cloud_cfg_filtered = cloud_init.cloud_cfg
    cloud_init_query = simple_command("/usr/bin/cloud-init query -f '{{ cloud_name, platform }}'")
    cloud_init_custom_network = simple_file("/etc/cloud/cloud.cfg.d/99-custom-networking.cfg")
    cloud_init_log = simple_file("/var/log/cloud-init.log")
    cluster_conf = simple_file("/etc/cluster/cluster.conf")
    cmdline = simple_file("/proc/cmdline")
    cni_podman_bridge_conf = simple_file("/etc/cni/net.d/87-podman-bridge.conflist")
    convert2rhel_facts = simple_file("/etc/rhsm/facts/convert2rhel.facts")
    corosync = simple_file("/etc/sysconfig/corosync")
    corosync_cmapctl = foreach_execute(corosync_ds.corosync_cmapctl_cmds, "%s")
    corosync_conf = simple_file("/etc/corosync/corosync.conf")
    cpu_cores = glob_file("sys/devices/system/cpu/cpu[0-9]*/online")
    cpu_siblings = glob_file("sys/devices/system/cpu/cpu[0-9]*/topology/thread_siblings_list")
    cpu_smt_active = simple_file("sys/devices/system/cpu/smt/active")
    cpu_vulns = glob_file("sys/devices/system/cpu/vulnerabilities/*")
    cpuinfo = simple_file("/proc/cpuinfo")
    cpupower_frequency_info = simple_command("/usr/bin/cpupower -c all frequency-info")
    cpuset_cpus = simple_file("/sys/fs/cgroup/cpuset/cpuset.cpus")
    cron_daily_rhsmd = simple_file("/etc/cron.daily/rhsmd")
    cron_foreman = simple_file("/etc/cron.d/foreman")
    cron_log = simple_file("/var/log/cron")
    crypto_policies_bind = simple_file("/etc/crypto-policies/back-ends/bind.config")
    crypto_policies_config = simple_file("/etc/crypto-policies/config")
    crypto_policies_opensshserver = simple_file(
        "/etc/crypto-policies/back-ends/opensshserver.config"
    )
    crypto_policies_state_current = simple_file("/etc/crypto-policies/state/current")
    cryptsetup_luksDump = luks.luks_data_sources
    cupsd_conf = simple_file("/etc/cups/cupsd.conf")
    cups_browsed_conf = simple_file("/etc/cups/cups-browsed.conf")
    cups_files_conf = simple_file("/etc/cups/cups-files.conf")
    current_clocksource = simple_file(
        "/sys/devices/system/clocksource/clocksource0/current_clocksource"
    )
    date = simple_command("/bin/date")
    date_utc = simple_command("/bin/date --utc")
    db2_database_configuration = foreach_execute(
        db2.db2_databases_info,
        "/usr/sbin/runuser -l  %s  -c 'db2 get database configuration for %s'",
    )
    db2_database_manager = foreach_execute(
        db2.db2_users, "/usr/sbin/runuser -l  %s  -c 'db2 get dbm cfg'"
    )
    db2ls_a_c = simple_command("/usr/local/bin/db2ls -a -c")
    df__al = simple_command("/bin/df -al -x autofs")
    df__alP = simple_command("/bin/df -alP -x autofs")
    df__li = simple_command("/bin/df -li -x autofs")
    dig_dnssec = simple_command("/usr/bin/dig +dnssec . SOA")
    dig_edns = simple_command("/usr/bin/dig +edns=0 . SOA")
    dig_noedns = simple_command("/usr/bin/dig +noedns . SOA")
    dirsrv_errors = glob_file("var/log/dirsrv/*/errors*")
    dm_mod_use_blk_mq = simple_file("/sys/module/dm_mod/parameters/use_blk_mq")
    dmesg = simple_command("/bin/dmesg")
    dmesg_log = simple_file("/var/log/dmesg")
    dmidecode = simple_command("/usr/sbin/dmidecode")
    dmsetup_info = simple_command("/usr/sbin/dmsetup info -C")
    dmsetup_status = simple_command("/usr/sbin/dmsetup status")
    dnf_conf = simple_file("/etc/dnf/dnf.conf")
    dnf_modules = glob_file("/etc/dnf/modules.d/*.module")  # used by puptoo
    dnf_module_list = simple_command(
        "/usr/bin/dnf -C --noplugins module list", signum=signal.SIGTERM
    )  # used by puptoo
    docker_info = simple_command("/usr/bin/docker info")  # v3.7.0
    docker_list_containers = simple_command("/usr/bin/docker ps --all --no-trunc")  # v3.7.0
    docker_list_images = simple_command(
        "/usr/bin/docker images --all --no-trunc --digests"
    )  # v3.7.0
    docker_storage_setup = simple_file("/etc/sysconfig/docker-storage-setup")  # v3.7.0
    docker_sysconfig = simple_file("/etc/sysconfig/docker")  # v3.7.0
    dotnet_version = simple_command("/usr/bin/dotnet --version")
    doveconf = simple_command("/usr/bin/doveconf")
    dracut_kdump_capture_service = simple_file(
        "/usr/lib/dracut/modules.d/99kdumpbase/kdump-capture.service"
    )
    dse_ldif = glob_file("/etc/dirsrv/*/dse.ldif")
    dumpe2fs_h = foreach_execute(mount_ds.dumpdev_list, "/sbin/dumpe2fs -h %s")
    du_dirs = foreach_execute(du.du_dir_list, "/bin/du -s -k %s")  # empty filter
    duplicate_machine_id = machine_id.dup_machine_id_info
    eap_json_reports = foreach_collect(eap_reports.eap_report_files, "%s")
    engine_log = simple_file("/var/log/ovirt-engine/engine.log")
    etc_journald_conf = simple_file(r"etc/systemd/journald.conf")
    etc_journald_conf_d = glob_file(r"etc/systemd/journald.conf.d/*.conf")
    etc_machine_id = simple_file("/etc/machine-id")
    etc_udev_40_redhat_rules = first_file(
        [
            "/etc/udev/rules.d/40-redhat.rules",
            "/run/udev/rules.d/40-redhat.rules",
            "/usr/lib/udev/rules.d/40-redhat.rules",
            "/usr/local/lib/udev/rules.d/40-redhat.rules",
        ]
    )
    etc_udev_oracle_asm_rules = glob_file(r"/etc/udev/rules.d/*asm*.rules")
    etcd_conf = simple_file("/etc/etcd/etcd.conf")
    ethtool = foreach_execute(ethernet.interfaces, "/sbin/ethtool %s")
    ethtool_S = foreach_execute(ethernet.interfaces, "/sbin/ethtool -S %s")
    ethtool_T = foreach_execute(ethernet.interfaces, "/sbin/ethtool -T %s")
    ethtool_c = foreach_execute(ethernet.interfaces, "/sbin/ethtool -c %s")
    ethtool_g = foreach_execute(ethernet.interfaces, "/sbin/ethtool -g %s")
    ethtool_i = foreach_execute(ethernet.interfaces, "/sbin/ethtool -i %s")
    ethtool_k = foreach_execute(ethernet.interfaces, "/sbin/ethtool -k %s")
    falconctl_aid = simple_command("/opt/CrowdStrike/falconctl -g --aid")
    falconctl_backend = simple_command("/opt/CrowdStrike/falconctl -g --backend")
    falconctl_rfm = simple_command("/opt/CrowdStrike/falconctl -g --rfm-state")
    falconctl_version = simple_command("/opt/CrowdStrike/falconctl -g --version")
    fapolicyd_rules = glob_file(r"/etc/fapolicyd/rules.d/*.rules")
    fcoeadm_i = simple_command("/usr/sbin/fcoeadm -i")
    files_dirs_number = ls.files_dirs_number
    filefrag = simple_command("/sbin/filefrag /boot/grub2/grubenv", keep_rc=True)
    findmnt_lo_propagation = simple_command("/bin/findmnt -lo+PROPAGATION")
    firewall_cmd_list_all_zones = simple_command("/usr/bin/firewall-cmd --list-all-zones")
    firewalld_conf = simple_file("/etc/firewalld/firewalld.conf")
    flatpak_list = simple_command("/usr/bin/flatpak list")
    foreman_production_log = simple_file("/var/log/foreman/production.log")
    fstab = simple_file("/etc/fstab")
    fw_security = first_of(
        [
            simple_command("/usr/bin/fwupdmgr security --force --json", deps=[IsBareMetal]),
            simple_command("/bin/fwupdagent security --force", deps=[IsBareMetal]),
        ]
    )
    galera_cnf = first_file(
        [
            "/var/lib/config-data/puppet-generated/mysql/etc/my.cnf.d/galera.cnf",
            "/etc/my.cnf.d/galera.cnf",
        ]
    )
    gcp_instance_type = simple_command(
        "/usr/bin/curl -s -H 'Metadata-Flavor: Google' 'http://metadata.google.internal/computeMetadata/v1/instance/machine-type' --connect-timeout 5",
        deps=[IsGCP],
    )
    gcp_license_codes = simple_command(
        "/usr/bin/curl -s -H 'Metadata-Flavor: Google' 'http://metadata.google.internal/computeMetadata/v1/instance/licenses/?recursive=True' --connect-timeout 5",
        deps=[IsGCP],
    )  # used by puptoo
    gcp_network_interfaces = simple_command(
        "/usr/bin/curl -s -H 'Metadata-Flavor: Google' 'http://metadata/computeMetadata/v1/instance/network-interfaces/?recursive=true' --connect-timeout 5",
        deps=[IsGCP],
    )
    getcert_list = simple_command("/usr/bin/getcert list")
    getconf_page_size = simple_command("/usr/bin/getconf PAGE_SIZE")
    getenforce = simple_command("/usr/sbin/getenforce")
    getsebool = simple_command("/usr/sbin/getsebool -a")
    gluster_v_info = simple_command("/usr/sbin/gluster volume info")
    greenboot_status = simple_command("/usr/libexec/greenboot/greenboot-status")  # used by puptoo
    group_info = command_with_args("/usr/bin/getent group %s", user_group.group_filters)
    grub1_config_perms = simple_command("/bin/ls -lH /boot/grub/grub.conf")  # RHEL6
    grub2_cfg = simple_file("/boot/grub2/grub.cfg")
    grub2_efi_cfg = simple_file("boot/efi/EFI/redhat/grub.cfg")
    grubby_default_index = simple_command(
        "/usr/sbin/grubby --default-index"
    )  # only RHEL7 and updwards
    grubby_default_kernel = simple_command("/sbin/grubby --default-kernel")
    grubby_info_all = simple_command("/usr/sbin/grubby --info=ALL")
    grub_conf = simple_file("/boot/grub/grub.conf")
    grub_config_perms = simple_command(
        "/bin/ls -lH /boot/grub2/grub.cfg"
    )  # only RHEL7 and updwards
    grub_efi_conf = simple_file("/boot/efi/EFI/redhat/grub.conf")
    grubenv = simple_command("/usr/bin/grub2-editenv list", keep_rc=True)
    haproxy_cfg = first_file(
        [
            "/var/lib/config-data/puppet-generated/haproxy/etc/haproxy/haproxy.cfg",
            "/etc/haproxy/haproxy.cfg",
        ]
    )
    haproxy_cfg_scl = simple_file("/etc/opt/rh/rh-haproxy18/haproxy/haproxy.cfg")
    heat_conf = first_file(
        ["/var/lib/config-data/puppet-generated/heat/etc/heat/heat.conf", "/etc/heat/heat.conf"]
    )
    hostname = simple_command("/bin/hostname -f")
    hostname_default = simple_command("/bin/hostname")
    hostname_short = simple_command("/bin/hostname -s")
    hosts = simple_file("/etc/hosts")
    hponcfg_g = simple_command("/sbin/hponcfg -g")
    httpd24_httpd_error_log = simple_file("/opt/rh/httpd24/root/etc/httpd/logs/error_log")
    httpd_M = foreach_execute(httpd.httpd_cmds, "%s -M")
    httpd_V = foreach_execute(httpd.httpd_cmds, "%s -V")
    httpd_cert_info_in_nss = foreach_execute(
        ssl_certificate.httpd_certificate_info_in_nss, '/usr/bin/certutil -d %s -L -n %s'
    )
    httpd_conf = foreach_collect(httpd.httpd_configuration_files, "%s")
    httpd_conf_scl_httpd24 = foreach_collect(httpd.httpd24_scl_configuration_files, "%s")
    httpd_conf_scl_jbcs_httpd24 = foreach_collect(httpd.httpd24_scl_jbcs_configuration_files, "%s")
    httpd_error_log = simple_file("var/log/httpd/error_log")
    httpd_limits = foreach_collect(httpd_pid, "/proc/%s/limits")
    httpd_on_nfs = httpd.httpd_on_nfs
    httpd_ssl_cert_enddate = foreach_execute(
        ssl_certificate.httpd_ssl_certificate_files, "/usr/bin/openssl x509 -in %s -enddate -noout"
    )
    ibm_fw_vernum_encoded = simple_file("/proc/device-tree/openprom/ibm,fw-vernum_encoded")
    ibm_lparcfg = simple_file("/proc/powerpc/lparcfg")
    ifcfg = glob_file("/etc/sysconfig/network-scripts/ifcfg-*")
    ifcfg_static_route = glob_file("/etc/sysconfig/network-scripts/route-*")
    ilab_config_show = simple_command("/usr/bin/ilab config show", inherit_env=['HOME'])
    ilab_model_list = simple_command("/usr/bin/ilab model list", inherit_env=['HOME'])
    imagemagick_policy = glob_file(
        ["/etc/ImageMagick/policy.xml", "/usr/lib*/ImageMagick-6.5.4/config/policy.xml"]
    )
    image_builder_facts = simple_file("/etc/rhsm/facts/osbuild.facts")
    init_process_cgroup = simple_file("/proc/1/cgroup")
    initctl_lst = simple_command("/sbin/initctl --system list")
    insights_client_conf = simple_file('/etc/insights-client/insights-client.conf')
    installed_rpms = simple_command(
        "/bin/rpm -qa --qf '{0}'".format(_rpm_format), context=HostContext, signum=signal.SIGTERM
    )
    interrupts = simple_file("/proc/interrupts")
    ip6tables = simple_command("/sbin/ip6tables-save")
    ip6tables_permanent = simple_file("etc/sysconfig/ip6tables")
    ip_addr = simple_command("/sbin/ip addr")
    ip_addresses = simple_command("/bin/hostname -I")
    ip_route_show_table_all = simple_command("/sbin/ip route show table all")
    ip_s_link = simple_command("/sbin/ip -s -d link")
    ipa_default_conf = simple_file("/etc/ipa/default.conf")  # RHINENG-14360
    ipaupgrade_log = simple_file("/var/log/ipaupgrade.log")
    ipcs_m = simple_command("/usr/bin/ipcs -m")
    ipcs_m_p = simple_command("/usr/bin/ipcs -m -p")
    ipcs_s = simple_command("/usr/bin/ipcs -s")
    ipcs_s_i = foreach_execute(ipcs.semid, "/usr/bin/ipcs -s -i %s")
    ipsec_conf = simple_file("/etc/ipsec.conf")
    iptables = simple_command("/sbin/iptables-save")
    iptables_permanent = simple_file("etc/sysconfig/iptables")
    ipv4_neigh = simple_command("/sbin/ip -4 neighbor show nud all")
    ipv6_neigh = simple_command("/sbin/ip -6 neighbor show nud all")
    iris_cpf = foreach_collect(intersystems.iris_working_configuration, "%s")
    iris_list = simple_command("/usr/bin/iris list")
    iris_messages_log = foreach_collect(intersystems.iris_working_messages_log, "%s")
    ironic_inspector_log = first_file(
        [
            "/var/log/containers/ironic-inspector/ironic-inspector.log",
            "/var/log/ironic-inspector/ironic-inspector.log",
        ]
    )
    iscsiadm_m_session = simple_command("/usr/sbin/iscsiadm -m session")
    jbcs_httpd24_httpd_error_log = simple_file("/opt/rh/jbcs-httpd24/root/etc/httpd/logs/error_log")
    jboss_runtime_versions = ps.jboss_runtime_versions
    journal_header = simple_command("/usr/bin/journalctl --no-pager --header")
    kdump_conf = simple_file("/etc/kdump.conf")
    kernel_config = glob_file("/boot/config-*")
    kernel_crash_kexec_post_notifiers = simple_file(
        "/sys/module/kernel/parameters/crash_kexec_post_notifiers"
    )
    kexec_crash_size = simple_file("/sys/kernel/kexec_crash_size")
    kpatch_list = simple_command("/usr/sbin/kpatch list")
    krb5 = glob_file([r"etc/krb5.conf", r"etc/krb5.conf.d/*"])
    ksmstate = simple_file("/sys/kernel/mm/ksm/run")
    lastupload = glob_file(
        ["/etc/redhat-access-insights/.lastupload", "/etc/insights-client/.lastupload"]
    )
    ld_library_path_global_conf = env.ld_library_path_global_conf
    leapp_migration_results = leapp.migration_results
    leapp_report = leapp.leapp_report
    ld_library_path_of_user = sap.ld_library_path_of_user
    libssh_client_config = simple_file("/etc/libssh/libssh_client.config")
    libssh_server_config = simple_file("/etc/libssh/libssh_server.config")
    libvirtd_log = simple_file("/var/log/libvirt/libvirtd.log")
    limits_conf = glob_file(["/etc/security/limits.conf", "/etc/security/limits.d/*.conf"])
    localectl_status = simple_command("/usr/bin/localectl status")
    localtime = simple_command("/usr/bin/file -L /etc/localtime")
    login_pam_conf = simple_file("/etc/pam.d/login")
    logrotate_conf = glob_file(["/etc/logrotate.conf", "/etc/logrotate.d/*"])
    losetup = simple_command("/usr/sbin/losetup -l")
    lpfc_max_luns = simple_file("/sys/module/lpfc/parameters/lpfc_max_luns")
    lpstat_p = simple_command("/usr/bin/lpstat -p")
    lpstat_protocol_printers = lpstat.lpstat_protocol_printers_info
    lpstat_queued_jobs_count = lpstat.lpstat_queued_jobs_count
    lru_gen_enabled = simple_file("/sys/kernel/mm/lru_gen/enabled")
    ls_la = command_with_args('/bin/ls -la %s', ls.list_with_la, keep_rc=True)
    ls_la_filtered = command_with_args(
        '/bin/ls -la %s', ls.list_with_la_filtered, keep_rc=True
    )  # Result is filtered
    ls_lan = command_with_args('/bin/ls -lan %s', ls.list_with_lan, keep_rc=True)
    ls_lan_filtered = command_with_args(
        '/bin/ls -lan %s', ls.list_with_lan_filtered, keep_rc=True
    )  # Result is filtered
    ls_lanL = command_with_args('/bin/ls -lanL %s', ls.list_with_lanL, keep_rc=True)
    ls_lanR = command_with_args('/bin/ls -lanR %s', ls.list_with_lanR, keep_rc=True)
    ls_lanRL = command_with_args('/bin/ls -lanRL %s', ls.list_with_lanRL, keep_rc=True)
    ls_laRZ = command_with_args('/bin/ls -laRZ %s', ls.list_with_laRZ, keep_rc=True)
    ls_laZ = command_with_args('/bin/ls -laZ %s', ls.list_with_laZ, keep_rc=True)
    ls_dev = simple_command("/bin/ls -lanR /dev")  # T.B.D
    ls_files = command_with_args('/bin/ls -lH %s', ls.list_files_with_lH, keep_rc=True)
    lsattr = command_with_args("/bin/lsattr %s", lsattr.paths_to_lsattr)
    lsblk = simple_command("/bin/lsblk")
    lsblk_pairs = simple_command(
        "/bin/lsblk -P -o NAME,KNAME,MAJ:MIN,FSTYPE,MOUNTPOINT,LABEL,UUID,RA,RO,RM,MODEL,SIZE,STATE,OWNER,GROUP,MODE,ALIGNMENT,MIN-IO,OPT-IO,PHY-SEC,LOG-SEC,ROTA,SCHED,RQ-SIZE,TYPE,DISC-ALN,DISC-GRAN,DISC-MAX,DISC-ZERO"
    )
    lscpu = simple_command("/usr/bin/lscpu")
    lsinitrd_kdump_image = command_with_args("/usr/bin/lsinitrd -k %skdump", kernel.current_version)
    lsmod = simple_command("/sbin/lsmod")
    lsof = first_of([simple_command("/usr/bin/lsof"), simple_command("/usr/sbin/lsof")])
    lspci = simple_command("/sbin/lspci -k")
    lspci_vmmkn = simple_command("/sbin/lspci -vmmkn")
    luksmeta = foreach_execute(
        block_devices_by_uuid, "/usr/bin/luksmeta show -d /dev/disk/by-uuid/%s", keep_rc=True
    )
    lvm_fullreport = simple_command("/sbin/lvm fullreport -a --nolocking --reportformat json")
    lvm_system_devices = simple_file("/etc/lvm/devices/system.devices")
    lvmconfig = first_of(
        [
            simple_command("/usr/sbin/lvmconfig --type full"),
            simple_command("/usr/sbin/lvm dumpconfig --type full"),
        ]
    )
    lvs_noheadings = simple_command(
        "/sbin/lvs --nameprefixes --noheadings --separator='|' -a -o lv_name,lv_size,lv_attr,mirror_log,vg_name,devices,region_size,data_percent,metadata_percent,segtype,seg_monitor,lv_kernel_major,lv_kernel_minor --config=\"global{locking_type=0}\""
    )
    mac_addresses = glob_file("/sys/class/net/*/address")
    machine_id = first_file(
        [
            "etc/insights-client/machine-id",
            "etc/redhat-access-insights/machine-id",
            "etc/redhat_access_proactive/machine-id",
        ]
    )
    mariadb_log = simple_file("/var/log/mariadb/mariadb.log")
    max_uid = simple_command(
        "/bin/awk -F':' '{ if($3 > max) max = $3 } END { print max }' /etc/passwd"
    )
    md5chk_files = foreach_execute(md5chk.files, "/usr/bin/md5sum %s", keep_rc=True)
    mdadm_D = command_with_args("/usr/sbin/mdadm -D %s", mdadm.raid_devices, keep_rc=True)
    mdstat = simple_file("/proc/mdstat")
    meminfo = first_file(["/proc/meminfo", "/meminfo"])
    messages = simple_file("/var/log/messages")
    modinfo_filtered_modules = command_with_args('modinfo %s', kernel.kernel_module_filters)
    modprobe = glob_file(["/etc/modprobe.conf", "/etc/modprobe.d/*.conf"])
    mokutil_sbstate = simple_command("/bin/mokutil --sb-state")
    mount = simple_command("/bin/mount")
    mountinfo = simple_file("/proc/self/mountinfo")
    mounts = simple_file("/proc/mounts")
    mssql_api_assessment = simple_file("/var/opt/mssql/log/assessments/assessment-latest")
    mssql_conf = simple_file("/var/opt/mssql/mssql.conf")
    mssql_tls_cert_enddate = command_with_args(
        "/usr/bin/openssl x509 -in %s -enddate -noout", ssl_certificate.mssql_tls_cert_file
    )
    multicast_querier = simple_command(
        r"/usr/bin/find /sys/devices/virtual/net/ -name multicast_querier -print -exec cat {} \;"
    )
    multipath__v4__ll = simple_command("/sbin/multipath -v4 -ll")
    multipath_conf = simple_file("/etc/multipath.conf")
    multipath_conf_initramfs = simple_command("/bin/lsinitrd -f /etc/multipath.conf")
    mysql_log = glob_file(
        [
            "/var/log/mysql/mysqld.log",
            "/var/log/mysql.log",
            "/var/opt/rh/rh-mysql*/log/mysql/mysqld.log",
        ]
    )
    mysqladmin_vars = simple_command("/bin/mysqladmin variables")
    named_checkconf_p = simple_command("/usr/sbin/named-checkconf -p")
    named_conf = simple_file("/etc/named.conf")
    ndctl_list_Ni = simple_command("/usr/bin/ndctl list -Ni")
    netstat = simple_command("/bin/netstat -neopa")
    netstat_i = simple_command("/bin/netstat -i")
    netstat_s = simple_command("/bin/netstat -s")
    networkmanager_conf = simple_file("/etc/NetworkManager/NetworkManager.conf")
    networkmanager_dispatcher_d = glob_file("/etc/NetworkManager/dispatcher.d/*-dhclient")
    nfnetlink_queue = simple_file("/proc/net/netfilter/nfnetlink_queue")
    nfs_conf = simple_file("/etc/nfs.conf")
    nfs_exports = simple_file("/etc/exports")
    nfs_exports_d = glob_file("/etc/exports.d/*.exports")
    nft_list_ruleset = simple_command("/sbin/nft -j list ruleset")
    nginx_conf = glob_file(
        [
            "/etc/nginx/*.conf",
            "/etc/nginx/conf.d/*.conf",
            "/etc/nginx/default.d/*.conf",
            "/opt/rh/nginx*/root/etc/nginx/*.conf",
            "/opt/rh/nginx*/root/etc/nginx/conf.d/*.conf",
            "/opt/rh/nginx*/root/etc/nginx/default.d/*.conf",
            "/etc/opt/rh/rh-nginx*/nginx/*.conf",
            "/etc/opt/rh/rh-nginx*/nginx/conf.d/*.conf",
            "/etc/opt/rh/rh-nginx*/nginx/default.d/*.conf",
        ]
    )

    nginx_error_log = first_of(
        [
            simple_file("/var/log/nginx/error.log"),
            head(glob_file("/var/opt/rh/rh-nginx*/log/nginx/error.log")),
        ]
    )
    nginx_ssl_cert_enddate = foreach_execute(
        ssl_certificate.nginx_ssl_certificate_files, "/usr/bin/openssl x509 -in %s -enddate -noout"
    )
    nmap_ssh = simple_command("/usr/bin/nmap --script ssh2-enum-algos -sV -p 22 127.0.0.1")
    nmcli_conn_show = simple_command("/usr/bin/nmcli conn show")
    nmcli_dev_show = simple_command("/usr/bin/nmcli dev show")
    nova_compute_log = first_file(
        ["/var/log/containers/nova/nova-compute.log", "/var/log/nova/nova-compute.log"]
    )
    nova_conf = first_file(
        [
            "/var/lib/config-data/puppet-generated/nova/etc/nova/nova.conf",
            "/var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/nova.conf",
            "/etc/nova/nova.conf",
        ]
    )
    nscd_conf = simple_file("/etc/nscd.conf")
    nss_rhel7 = simple_file("/etc/pki/nss-legacy/nss-rhel7.config")
    nsswitch_conf = simple_file("/etc/nsswitch.conf")
    ntp_conf = simple_file("/etc/ntp.conf")
    ntpq_pn = simple_command("/usr/sbin/ntpq -pn")
    numa_cpus = glob_file("/sys/devices/system/node/node[0-9]*/cpulist")
    numeric_user_group_name = simple_command("/bin/grep -c '^[[:digit:]]' /etc/passwd /etc/group")
    nvidia_smi_active_clocks_event_reasons = simple_command(
        "/usr/bin/nvidia-smi --query-gpu=name,clocks_event_reasons.active --format=csv,noheader"
    )
    nvidia_smi_l = simple_command("/usr/bin/nvidia-smi -L")
    nvidia_smi_query_gpu = simple_command(
        "/usr/bin/nvidia-smi --query-gpu=index,name,uuid,memory.total --format=csv,noheader"
    )  # make sure not break the command collection when adding new options
    nvme_core_io_timeout = simple_file("/sys/module/nvme_core/parameters/io_timeout")
    od_cpu_dma_latency = simple_command("/usr/bin/od -An -t d /dev/cpu_dma_latency")
    odbc_ini = simple_file("/etc/odbc.ini")
    odbcinst_ini = simple_file("/etc/odbcinst.ini")
    openshift_router_environ = foreach_collect(openshift_router_pid, "/proc/%s/environ")
    os_release = simple_file("etc/os-release")
    ose_master_config = simple_file("/etc/origin/master/master-config.yaml")
    ose_node_config = simple_file("/etc/origin/node/node-config.yaml")
    ovirt_engine_server_log = simple_file("/var/log/ovirt-engine/server.log")
    ovirt_engine_ui_log = simple_file("/var/log/ovirt-engine/ui.log")
    ovs_appctl_fdb_show_bridge = foreach_execute(
        ovs_vsctl_list_br, "/usr/bin/ovs-appctl fdb/show %s"
    )
    ovs_vsctl_list_bridge = simple_command("/usr/bin/ovs-vsctl list bridge")
    ovs_vsctl_show = simple_command("/usr/bin/ovs-vsctl show")
    pacemaker_log = first_file(["/var/log/pacemaker.log", "/var/log/pacemaker/pacemaker.log"])
    package_provides_command = package_provides.cmd_and_pkg
    parted__l = simple_command("/sbin/parted -l -s")
    password_auth = simple_file("/etc/pam.d/password-auth")
    pci_rport_target_disk_paths = simple_command(
        "/usr/bin/find /sys/devices/ -maxdepth 10 -mindepth 9 -name stat -type f"
    )
    pcp_metrics = simple_command(
        "/usr/bin/curl -s http://127.0.0.1:44322/metrics --connect-timeout 5", deps=[pcp_enabled]
    )
    pcp_raw_data = foreach_collect(
        pcp_raw_files, "%s", save_as="var/log/pcp/pmlogger/", kind=RawFileProvider
    )
    pcs_quorum_status = simple_command("/usr/sbin/pcs quorum status")
    pcs_status = simple_command("/usr/sbin/pcs status")
    pidstat = simple_command("/usr/bin/pidstat")
    php_ini = first_file(["/etc/opt/rh/php73/php.ini", "/etc/opt/rh/php72/php.ini", "/etc/php.ini"])
    pluginconf_d = glob_file("/etc/yum/pluginconf.d/*.conf")
    pmlog_summary = command_with_args("/usr/bin/pmlogsummary %s", pmlog_summary_args)
    pmlog_summary_pcp_zeroconf = command_with_args(
        "/usr/bin/pmlogsummary %s",
        pmlog_summary_args_pcp_zeroconf,
        save_as='pmlogsummary_based_on_pcp_zeroconf_archives',
    )
    pmrep_metrics = simple_command(
        "/usr/bin/pmrep -t 1s -T 1s network.interface.out.packets network.interface.collisions swap.pagesout mssql.memory_manager.stolen_server_memory mssql.memory_manager.total_server_memory -o csv"
    )
    podman_list_containers = simple_command("/usr/bin/podman ps --all --no-trunc")
    postconf = simple_command("/usr/sbin/postconf")
    postconf_builtin = simple_command("/usr/sbin/postconf -C builtin")
    postfix_master = simple_file("/etc/postfix/master.cf")
    postgresql_conf = first_file(
        [
            "/var/opt/rh/rh-postgresql12/lib/pgsql/data/postgresql.conf",
            "/var/lib/pgsql/data/postgresql.conf",
        ]
    )
    postgresql_log = first_of(
        [
            glob_file("/var/opt/rh/rh-postgresql12/lib/pgsql/data/log/postgresql-*.log"),
            glob_file("/var/lib/pgsql/data/pg_log/postgresql-*.log"),
        ]
    )
    proc_keys = simple_file("/proc/keys")
    proc_keyusers = simple_file("/proc/key-users")
    proc_netstat = simple_file("proc/net/netstat")
    proc_slabinfo = simple_file("proc/slabinfo")
    proc_snmp_ipv4 = simple_file("proc/net/snmp")
    proc_snmp_ipv6 = simple_file("proc/net/snmp6")
    proc_stat = simple_file("proc/stat")
    ps_alxwww = simple_command("/bin/ps alxwww")
    ps_aux = simple_command("/bin/ps aux")
    ps_auxcww = simple_command("/bin/ps auxcww")
    ps_auxww = simple_command("/bin/ps auxww")
    ps_ef = simple_command("/bin/ps -ef")
    ps_eo = simple_command("/usr/bin/ps -eo pid,ppid,comm,nlwp")
    ps_eo_cmd = ps.ps_eo_cmd
    puppet_ca_cert_expire_date = simple_command(
        "/usr/bin/openssl x509 -in /etc/puppetlabs/puppet/ssl/ca/ca_crt.pem -enddate -noout"
    )
    pvs_noheadings = simple_command(
        "/sbin/pvs --nameprefixes --noheadings --separator='|' -a -o pv_all,vg_name --config=\"global{locking_type=0}\""
    )
    rhsm_katello_default_ca_cert = simple_command(
        "/usr/bin/openssl x509 -in /etc/rhsm/ca/katello-default-ca.pem -noout -issuer"
    )
    qemu_xml = glob_file(r"/etc/libvirt/qemu/*.xml")
    ql2xmaxlun = simple_file("/sys/module/qla2xxx/parameters/ql2xmaxlun")
    ql2xmqsupport = simple_file("/sys/module/qla2xxx/parameters/ql2xmqsupport")
    random_entropy_avail = simple_file("/proc/sys/kernel/random/entropy_avail")
    rc_local = simple_file("/etc/rc.d/rc.local")
    readlink_e_etc_mtab = simple_command("/usr/bin/readlink -e /etc/mtab")
    readlink_e_shift_cert_client = simple_command(
        "/usr/bin/readlink -e /etc/origin/node/certificates/kubelet-client-current.pem"
    )
    readlink_e_shift_cert_server = simple_command(
        "/usr/bin/readlink -e /etc/origin/node/certificates/kubelet-server-current.pem"
    )
    rear_local_conf = simple_file("/etc/rear/local.conf")
    redhat_release = simple_file("/etc/redhat-release")
    repquota_agnpuv = simple_command("/usr/sbin/repquota -agnpuv")
    resolv_conf = simple_file("/etc/resolv.conf")
    rhc_conf = simple_file('/etc/rhc/config.toml')
    rhsm_conf = simple_file("/etc/rhsm/rhsm.conf")
    rhsm_releasever = simple_file('/var/lib/rhsm/cache/releasever.json')
    rhui_releasever = first_file(
        [
            '/etc/dnf/vars/releasever',
            '/etc/yum/vars/releasever',
        ]
    )
    rndc_status = simple_command("/usr/sbin/rndc status")
    ros_config = simple_file("/var/lib/pcp/config/pmlogger/config.ros")
    rpm_V_package = foreach_execute(
        rpm.rpm_v_pkg_list, "/bin/rpm -V %s", keep_rc=True, signum=signal.SIGTERM
    )
    rpm_ostree_status = simple_command("/usr/bin/rpm-ostree status --json", signum=signal.SIGTERM)
    rpm_pkgs = rpm.pkgs_with_writable_dirs
    rsyslog_conf = glob_file(["/etc/rsyslog.conf", "/etc/rsyslog.d/*.conf"])
    rsyslog_tls_ca_cert_enddate = command_with_args(
        "/usr/bin/openssl x509 -in %s -enddate -noout", ssl_certificate.rsyslog_tls_ca_cert_file
    )
    rsyslog_tls_cert_enddate = command_with_args(
        "/usr/bin/openssl x509 -in %s -enddate -noout", ssl_certificate.rsyslog_tls_cert_file
    )
    samba = simple_file("/etc/samba/smb.conf")
    sap_hana_landscape = foreach_execute(
        sap_hana_sid_SID_nr,
        "/bin/su -l %sadm -c 'python /usr/sap/%s/HDB%s/exe/python_support/landscapeHostConfiguration.py'",
        keep_rc=True,
    )
    sap_hdb_version = foreach_execute(
        sap_hana_sid, "/bin/su -l %sadm -c 'HDB version'", keep_rc=True
    )
    saphostctl_getcimobject_sapinstance = simple_command(
        "/usr/sap/hostctrl/exe/saphostctrl -function GetCIMObject -enuminstances SAPInstance"
    )
    satellite_compute_resources = simple_command(
        "/usr/bin/sudo -iu postgres /usr/bin/psql -d foreman -c 'select name, type from compute_resources' --csv",
        deps=[IsSatellite],
    )
    satellite_content_hosts_count = simple_command(
        "/usr/bin/sudo -iu postgres /usr/bin/psql -d foreman -c 'select count(*) from hosts'",
        deps=[IsSatellite],
    )
    satellite_custom_ca_chain = simple_command(
        '/usr/bin/awk \'BEGIN { pipe="openssl x509 -noout -subject -enddate"} /^-+BEGIN CERT/,/^-+END CERT/ { print | pipe } /^-+END CERT/ { close(pipe); printf("\\n")}\' /etc/pki/katello/certs/katello-server-ca.crt',
    )
    satellite_custom_hiera = simple_file("/etc/foreman-installer/custom-hiera.yaml")
    satellite_enabled_features = simple_command(
        "/usr/bin/curl -sk https://localhost:9090/features --connect-timeout 5", deps=[IsSatellite]
    )
    satellite_host_facts_count = simple_command(
        "/usr/bin/sudo -iu postgres /usr/bin/psql -d foreman -c 'select count(*) from fact_names' --csv",
        deps=[IsSatellite],
    )
    satellite_ignore_source_rpms_repos = simple_command(
        "/usr/bin/sudo -iu postgres /usr/bin/psql -d foreman -c \"select id, name from katello_root_repositories where ignorable_content like '%srpm%' and mirroring_policy='mirror_complete'\" --csv",
        deps=[IsSatellite],
    )
    satellite_logs_table_size = simple_command(
        "/usr/bin/sudo -iu postgres /usr/bin/psql -d foreman -c \"select pg_total_relation_size('logs') as logs_size\" --csv",
        deps=[IsSatellite],
    )
    satellite_missed_pulp_agent_queues = satellite.satellite_missed_pulp_agent_queues
    satellite_provision_param_settings = simple_command(
        "/usr/bin/sudo -iu postgres /usr/bin/psql -d foreman -c \"select name, value from parameters where name='package_upgrade' and reference_id in (select id from operatingsystems where name='RedHat' and major='9')\" --csv",
        deps=[IsSatellite611],
    )
    satellite_qualified_capsules = simple_command(
        "/usr/bin/sudo -iu postgres /usr/bin/psql -d foreman -c \"select name from smart_proxies where download_policy = 'background'\" --csv",
        deps=[IsSatellite],
    )
    satellite_qualified_katello_repos = simple_command(
        "/usr/bin/sudo -iu postgres /usr/bin/psql -d foreman -c \"select id, name, url, download_policy from katello_root_repositories where download_policy = 'background' or url is NULL\" --csv",
        deps=[IsSatellite],
    )
    satellite_revoked_cert_count = simple_command(
        "/usr/bin/sudo -iu postgres /usr/bin/psql -d candlepin -c \"select count(cp_certificate.id) from cp_cert_serial inner join cp_certificate on cp_certificate.serial_id = cp_cert_serial.id where cp_cert_serial.revoked = 't'\" --csv",
        deps=[IsSatellite],
    )
    satellite_rhv_hosts_count = simple_command(
        "/usr/bin/sudo -iu postgres /usr/bin/psql -d foreman -c \"select count(*) from hosts where \"compute_resource_id\" in (select id from compute_resources where type='Foreman::Model::Ovirt')\" --csv",
        deps=[IsSatellite],
    )
    satellite_settings = first_of(
        [
            simple_command(
                "/usr/bin/sudo -iu postgres /usr/bin/psql -d foreman -c \"select name, value, \\\"default\\\" from settings where name in ('destroy_vm_on_host_delete', 'unregister_delete_host')\" --csv",
                deps=[IsSatelliteLessThan614],
            ),
            simple_command(
                "/usr/bin/sudo -iu postgres /usr/bin/psql -d foreman -c \"select name, value from settings where name in ('destroy_vm_on_host_delete', 'unregister_delete_host')\" --csv",
                deps=[IsSatellite614AndLater],
            ),
        ]
    )
    satellite_version_rb = simple_file("/usr/share/foreman/lib/satellite/version.rb")
    satellite_yaml = simple_file("/etc/foreman-installer/scenarios.d/satellite.yaml")
    scheduler = glob_file("/sys/block/*/queue/scheduler")
    scsi = simple_file("/proc/scsi/scsi")
    scsi_eh_deadline = glob_file('/sys/class/scsi_host/host[0-9]*/eh_deadline')
    scsi_fwver = glob_file('/sys/class/scsi_host/host[0-9]*/fwrev')
    scsi_mod_max_report_luns = simple_file("/sys/module/scsi_mod/parameters/max_report_luns")
    scsi_mod_use_blk_mq = simple_file("/sys/module/scsi_mod/parameters/use_blk_mq")
    sctp_asc = simple_file('/proc/net/sctp/assocs')
    sctp_eps = simple_file('/proc/net/sctp/eps')
    sctp_snmp = simple_file('/proc/net/sctp/snmp')
    sealert = simple_command('/usr/bin/sealert -l "*"', deps=[SELinuxEnabled])
    secure = simple_file("/var/log/secure")
    securetty = simple_file("/etc/securetty")
    selinux_config = simple_file("/etc/selinux/config")
    sendmail_mc = simple_file("/etc/mail/sendmail.mc")
    sestatus = simple_command("/usr/sbin/sestatus -b")
    setup_named_chroot = simple_file("/usr/libexec/setup-named-chroot.sh")
    smartctl_health = foreach_execute(dev.physical_devices, "/usr/sbin/smartctl -H %s -j")
    smbstatus_p = simple_command("/usr/bin/smbstatus -p")
    snmpd_conf = simple_file("/etc/snmp/snmpd.conf")
    sockstat = simple_file("/proc/net/sockstat")
    softnet_stat = simple_file("proc/net/softnet_stat")
    software_collections_list = simple_command('/usr/bin/scl --list')
    sos_conf = first_file(["/etc/sos/sos.conf", "/etc/sos.conf"])
    spamassassin_channels = simple_command(
        "/bin/grep -r '^\\s*CHANNELURL=' /etc/mail/spamassassin/channel.d"
    )
    squid_cache_log = simple_file("/var/log/squid/cache.log")
    ss = simple_command("/usr/sbin/ss -tupna")
    ssh_config = simple_file("/etc/ssh/ssh_config")
    ssh_config_d = glob_file(r"/etc/ssh/ssh_config.d/*.conf")
    sshd_config = simple_file("/etc/ssh/sshd_config")
    sshd_config_d = glob_file(r"/etc/ssh/sshd_config.d/*.conf")
    sshd_config_perms = simple_command("/bin/ls -lH /etc/ssh/sshd_config")
    sshd_test_mode = simple_command("/usr/sbin/sshd -T")
    sssd_config = simple_file("/etc/sssd/sssd.conf")
    sssd_conf_d = glob_file("/etc/sssd/conf.d/*.conf")
    subscription_manager_facts = simple_command(
        "/usr/sbin/subscription-manager facts", override_env={"LC_ALL": "C.UTF-8"}
    )
    subscription_manager_id = simple_command(
        "/usr/sbin/subscription-manager identity",  # use "/usr/sbin" here, BZ#1690529
        override_env={"LC_ALL": "C.UTF-8"},
    )
    subscription_manager_installed_product_ids = simple_command(
        r"/usr/bin/find /etc/pki/product-default/ /etc/pki/product/ -name '*pem' -exec rct cat-cert --no-content '{}' \;"
    )
    subscription_manager_status = simple_command(
        "/usr/sbin/subscription-manager status", override_env={"LC_ALL": "C.UTF-8"}
    )
    subscription_manager_syspurpose = simple_command(
        "/usr/sbin/subscription-manager syspurpose --show",
        deps=[IsGtOrRhel84],
        override_env={"LC_ALL": "C.UTF-8"},
    )
    sudoers = glob_file(["/etc/sudoers", "/etc/sudoers.d/*"])
    swift_proxy_server_conf = first_file(
        [
            "/var/lib/config-data/puppet-generated/swift/etc/swift/proxy-server.conf",
            "/etc/swift/proxy-server.conf",
        ]
    )
    sys_block_queue_stable_writes = glob_file("/sys/block/*/queue/stable_writes")
    sys_fs_cgroup_memory_tasks_number = sys_fs_cgroup_memory.tasks_number
    sys_fs_cgroup_uniq_memory_swappiness = sys_fs_cgroup_memory.uniq_memory_swappiness
    sys_vmbus_class_id = glob_file('/sys/bus/vmbus/devices/*/class_id')
    sys_vmbus_device_id = glob_file('/sys/bus/vmbus/devices/*/device_id')
    sysconfig_grub = simple_file(
        "/etc/default/grub"
    )  # This is the file where the "/etc/sysconfig/grub" point to
    sysconfig_irqbalance = simple_file("/etc/sysconfig/irqbalance")
    sysconfig_kdump = simple_file("etc/sysconfig/kdump")
    sysconfig_kernel = simple_file("etc/sysconfig/kernel")
    sysconfig_libvirt_guests = simple_file("etc/sysconfig/libvirt-guests")
    sysconfig_network = simple_file("etc/sysconfig/network")
    sysconfig_nfs = simple_file("/etc/sysconfig/nfs")
    sysconfig_ntpd = simple_file("/etc/sysconfig/ntpd")
    sysconfig_oracleasm = simple_file("/etc/sysconfig/oracleasm")
    sysconfig_pcsd = simple_file("/etc/sysconfig/pcsd")
    sysconfig_prelink = simple_file("/etc/sysconfig/prelink")
    sysconfig_sbd = simple_file("/etc/sysconfig/sbd")
    sysconfig_sshd = simple_file("/etc/sysconfig/sshd")
    sysconfig_stonith = simple_file("/etc/sysconfig/stonith")
    sysctl = simple_command("/sbin/sysctl -a")
    sysctl_conf = simple_file("/etc/sysctl.conf")
    sysctl_d_conf_etc = glob_file("/etc/sysctl.d/*.conf")
    sysctl_d_conf_usr = glob_file("/usr/lib/sysctl.d/*.conf")
    systemctl_cat_rpcbind_socket = simple_command("/bin/systemctl cat rpcbind.socket")
    systemctl_get_default = simple_command("/bin/systemctl get-default")
    systemctl_list_unit_files = simple_command("/bin/systemctl list-unit-files")
    systemctl_list_units = simple_command("/bin/systemctl list-units")
    systemctl_show_all_services = simple_command("/bin/systemctl show *.service")
    systemctl_show_target = simple_command("/bin/systemctl show *.target")
    systemctl_status_all = simple_command("/bin/systemctl status --all")  # used by puptoo
    systemd_analyze_blame = simple_command("/bin/systemd-analyze blame")
    systemd_docker = simple_command("/usr/bin/systemctl cat docker.service")  # v3.7.0
    systemd_logind_conf = simple_file("/etc/systemd/logind.conf")
    systemd_openshift_node = simple_command("/usr/bin/systemctl cat atomic-openshift-node.service")
    systemd_system_conf = simple_file("/etc/systemd/system.conf")
    systemid = first_of(
        [
            simple_file("/etc/sysconfig/rhn/systemid"),
            simple_file("/conf/rhn/sysconfig/rhn/systemid"),
        ]
    )  # XML
    teamdctl_config_dump = foreach_execute(
        ethernet.team_interfaces, "/usr/bin/teamdctl %s config dump"
    )
    teamdctl_state_dump = foreach_execute(
        ethernet.team_interfaces, "/usr/bin/teamdctl %s state dump"
    )
    testparm_s = simple_command("/usr/bin/testparm -s")
    testparm_v_s = simple_command("/usr/bin/testparm -v -s")
    thp_enabled = simple_file("/sys/kernel/mm/transparent_hugepage/enabled")
    thp_use_zero_page = simple_file("/sys/kernel/mm/transparent_hugepage/use_zero_page")
    timedatectl_status = simple_command('/usr/bin/timedatectl status')
    tmpfilesd = glob_file(
        ["/etc/tmpfiles.d/*.conf", "/usr/lib/tmpfiles.d/*.conf", "/run/tmpfiles.d/*.conf"]
    )
    tomcat_web_xml = first_of(
        [glob_file("/etc/tomcat*/web.xml"), glob_file("/conf/tomcat/tomcat*/web.xml")]
    )
    tomcat_vdc_fallback = simple_command(
        "/usr/bin/find /usr/share -maxdepth 1 -name 'tomcat*' -exec /bin/grep -R -s 'VirtualDirContext' --include '*.xml' '{}' +"
    )
    tty_console_active = simple_file("sys/class/tty/console/active")
    tuned_adm = simple_command("/usr/sbin/tuned-adm list")
    udev_66_md_rules = first_file(
        ["/etc/udev/rules.d/66-md-auto-readd.rules", "/usr/lib/udev/rules.d/66-md-auto-readd.rules"]
    )
    udev_fc_wwpn_id_rules = simple_file("/usr/lib/udev/rules.d/59-fc-wwpn-id.rules")
    uname = first_of(
        [simple_command("/usr/bin/uname -a"), simple_command("/bin/uname -a")]  # RHEL 6
    )
    up2date = simple_file("/etc/sysconfig/rhn/up2date")
    up2date_log = simple_file("/var/log/up2date")
    uptime = simple_command("/usr/bin/uptime")
    usr_journald_conf_d = glob_file(
        r"usr/lib/systemd/journald.conf.d/*.conf"
    )  # note that etc_journald.conf.d also exists
    vdo_status = simple_command("/usr/bin/vdo status")
    vdsm_log = simple_file("var/log/vdsm/vdsm.log")
    vgdisplay = simple_command("/sbin/vgdisplay")
    vgs_noheadings = simple_command(
        "/sbin/vgs --nameprefixes --noheadings --separator='|' -a -o vg_all --config=\"global{locking_type=0}\""
    )
    vgs_with_foreign_and_shared = simple_command(
        "/sbin/vgs --nameprefixes --noheadings --separator='|' -a -o vg_all --nolocking --foreign --shared"
    )
    virsh_list_all = simple_command("/usr/bin/virsh --readonly list --all")
    virt_what = simple_command("/usr/sbin/virt-what")
    vma_ra_enabled = simple_file("/sys/kernel/mm/swap/vma_ra_enabled")
    vsftpd = simple_file("/etc/pam.d/vsftpd")
    vsftpd_conf = simple_file("/etc/vsftpd/vsftpd.conf")
    watchdog_logs = glob_file("/var/log/watchdog/*.std*")
    wc_proc_1_mountinfo = simple_command("/usr/bin/wc -l /proc/1/mountinfo")
    x86_ibpb_enabled = simple_file("sys/kernel/debug/x86/ibpb_enabled")
    x86_ibrs_enabled = simple_file("sys/kernel/debug/x86/ibrs_enabled")
    x86_pti_enabled = simple_file("sys/kernel/debug/x86/pti_enabled")
    x86_retp_enabled = simple_file("sys/kernel/debug/x86/retp_enabled")
    xfs_info = foreach_execute(mount_ds.xfs_mounts, "/usr/sbin/xfs_info %s")  # INSPEC-409
    xfs_quota_state = simple_command("/sbin/xfs_quota -x -c 'state -gu'")
    xinetd_conf = glob_file(["/etc/xinetd.conf", "/etc/xinetd.d/*"])
    yum_conf = simple_file("/etc/yum.conf")
    yum_list_available = simple_command("yum -C --noplugins list available", signum=signal.SIGTERM)
    yum_log = simple_file("/var/log/yum.log")
    yum_repolist = simple_command(
        "/usr/bin/yum -d 2 -C --noplugins repolist",
        override_env={"LC_ALL": ""},
        signum=signal.SIGTERM,
    )
    yum_repos_d = glob_file("/etc/yum.repos.d/*.repo")
    yum_updates = yum_updates.yum_updates  # used by puptoo
    zipl_conf = simple_file("/etc/zipl.conf")

    # Container collection specs
    container_cpu_online = container_collect(
        running_rhel_containers, "/sys/devices/system/cpu/online"
    )
    container_cpuset_cpus = container_collect(
        running_rhel_containers, "/sys/fs/cgroup/cpuset/cpuset.cpus"
    )
    container_dotnet_version = container_execute(
        running_rhel_containers, "/usr/bin/dotnet --version"
    )
    container_installed_rpms = container_execute(
        running_rhel_containers,
        "/usr/bin/rpm -qa --qf '{0}'".format(_rpm_format),
        context=HostContext,
        signum=signal.SIGTERM,
    )
    container_mssql_api_assessment = container_collect(
        running_rhel_containers, "/var/opt/mssql/log/assessments/assessment-latest"
    )
    container_nginx_conf = container_collect(container_nginx_conf_ds)
    container_nginx_error_log = container_collect(
        running_rhel_containers, "/var/log/nginx/error.log"
    )
    container_ps_aux = container_execute(running_rhel_containers, "/bin/ps aux")
    container_redhat_release = container_collect(running_rhel_containers, "/etc/redhat-release")
    container_vsftpd_conf = container_collect(running_rhel_containers, "/etc/vsftpd/vsftpd.conf")
    containers_inspect = containers_inspect.containers_inspect_data_datasource
