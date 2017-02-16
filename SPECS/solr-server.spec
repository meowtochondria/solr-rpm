# Copyright (c) 2015 Jason Stafford
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Some documentation to help reduce time to search
# https://fedoraproject.org/wiki/How_to_create_an_RPM_package#SPEC_file_overview

# RPM Build reference:
# http://www.tldp.org/HOWTO/RPM-HOWTO/build.html
# http://rpm-guide.readthedocs.io/en/latest/rpm-guide.html#rpm-packages

# Disable repacking of jars, since it takes forever
# and it is not needed since there are no platform dependent jars in the archive
%define __jar_repack %{nil}

# Rationale: http://www.pathname.com/fhs/pub/fhs-2.3.html#THEUSRHIERARCHY
%define solr_install_dir /usr/local/solr-%{solr_version}
# Solr installation symlink. Use this in scripts and paths.
%define solr_install_link /usr/local/solr
# path where solr will log.
%define solr_log_dir /var/log/solr
# Rationale: http://www.pathname.com/fhs/pub/fhs-2.3.html#SRVDATAFORSERVICESPROVIDEDBYSYSTEM
%define solr_data_dir /srv/solr
# path where solr configurations will be stored
%define solr_config_dir /etc/solr
# binary files that allow us to control solr
%define solr_bin_dir /usr/local/bin/solr
# path where runtime files (like PID file) will be located
%define solr_run_dir /run/solr
# directory for holding file that contains environment variables
%define solr_env_dir /etc/default
# directory that will hold SystemD service definition for solr
%define solr_service_dir /lib/systemd/system
# matches SOLR_USER in the install_solr_service.sh file
%define solr_user solr
# matches SOLR_PORT in the install_solr_service.sh file
%define solr_port 8983
# name of the SystemD unit file
%define solr_service solr-server.service
# string to append when backing up to upgrade
%define solr_backup_str upgrading_to_%{solr_version}
# file containing all the files installed by this rpm.
%define packaged_files %{_builddir}/packaged_files.txt


Name:           solr-server
Version:        %{solr_version}
Release:        %{rpm_release}
Summary:        Solr is the popular, blazing-fast, open source enterprise search platform built on Apache Lucene™
# We download and verify the binary archive in build.sh
Source0:        solr-%{solr_version}.tgz
URL:            http://lucene.apache.org/solr/
Group:          System Environment/Daemons
License:        Apache License, Version 2.0
Requires:       java-1.8.0-openjdk-headless >= 1.8.0, systemd, lsof, gawk, coreutils, shadow-utils
BuildArch:      noarch
BuildRequires:  tar, sed, coreutils
Vendor:         Apache Software Foundation

%description
Solr is an open source enterprise search server based on the Lucene Java search
library, with XML/HTTP and JSON APIs, hit highlighting, faceted search,
caching, replication, and a web administration interface. It runs in a Java 
servlet container such as Jetty.

This package provides binaries for running the server distribution
from the official website in RPM form. It includes embedded Jetty.

%prep
%setup -q -b 0 -n solr-%{solr_version}
# Copy SystemD service definition to SOURCES... 
cp -p %{_topdir}/../extra/%{solr_service} %{_builddir}/

# Do some substitutions in scripts and configs to reflect constants defined in this spec file.
# Substitutions in place of patches will make maintenance easier.
solr_env_file='%{_builddir}/solr-%{solr_version}/bin/solr.in.sh'
sed -i'' 's|#SOLR_PID_DIR=|SOLR_PID_DIR=%{solr_run_dir}|g' $solr_env_file
sed -i'' 's|#SOLR_HOME=|SOLR_HOME=%{solr_data_dir}|g' $solr_env_file
sed -i'' 's|#LOG4J_PROPS=|LOG4J_PROPS=%{solr_config_dir}/log4j.properties|g' $solr_env_file
sed -i'' 's|#SOLR_LOGS_DIR=|SOLR_LOGS_DIR=%{solr_log_dir}|g' $solr_env_file

# Update paths in service definition
systemd_unit_file="%{_builddir}/%{solr_service}"
sed -i'' 's|RPM_PORT|%{solr_port}|g' $systemd_unit_file
sed -i'' 's|RPM_ENV_DIR|%{solr_env_dir}|g' $systemd_unit_file
sed -i'' 's|RPM_RUN_DIR|%{solr_run_dir}|g' $systemd_unit_file
sed -i'' 's|RPM_BIN_DIR|%{solr_bin_dir}|g' $systemd_unit_file
sed -i'' 's|RPM_INSTALL_DIR|%{solr_install_link}|g' $systemd_unit_file

# Because we are not packaging dist and 'post' script depends on it,
# change the path of solr-core.*.jar to the one that is packaged here.
# Source code analysis shows the util class used by 'post' script is
# there in solr-core in server too.
sed -i 's|"$SOLR_TIP/dist"|%{solr_install_link}/server/solr-webapp/webapp/WEB-INF/lib|g' bin/post
 
%build

%install
rm -rf "%{buildroot}"

# make all directories.
for dir in %{solr_install_dir} %{solr_log_dir} %{solr_run_dir} %{solr_data_dir} %{solr_config_dir} %{solr_bin_dir} %{solr_env_dir} %{solr_service_dir}
do
  %__install -d "%{buildroot}$dir"
done

solr_root="%{_builddir}/solr-%{solr_version}"
# install the main solr package in solr_install_dir
cp -Rp "$solr_root/server" "%{buildroot}%{solr_install_dir}/"

# Bin files/scripts.
# Do not copy Windows specific things and files that will not be living in bin folder.
for file in oom_solr.sh post solr; do
  cp -Rp "$solr_root/bin/$file" "%{buildroot}%{solr_bin_dir}/$file"
done

# copy config
cp -p $solr_root/server/solr/solr.xml "%{buildroot}%{solr_data_dir}/"
cp -p $solr_root/bin/solr.in.sh "%{buildroot}%{solr_env_dir}/"
cp -p $solr_root/server/resources/log4j.properties "%{buildroot}%{solr_config_dir}/"

# install the systemd unit definition to /lib/systemd/system (works both on Debian and CentOS)
%__install -m0744 %{_builddir}/%{solr_service} "%{buildroot}%{solr_service_dir}/"

# copy licenses and other text files.
cp -Rp $solr_root/licenses %{buildroot}%{solr_install_dir}/
cp -p  $solr_root/*.txt %{buildroot}%{solr_install_dir}/

# build the list of files packaged in this archive.
[ -f %{packaged_files} ] && rm -f %{packaged_files}
find %{buildroot} -type f -name '*' -print | sed 's,%{buildroot},,g' > %{packaged_files}

%pre
id -u %{solr_user} &> /dev/null
if [ "$?" -ne "0" ]; then
  # useradd is low-level utility and works on most distros.
  # -M Do no create the user's home directory, even if the system wide setting from
  #    /etc/login.defs (CREATE_HOME) is set to yes.
  # /usr/sbin/nologin exists on RedHat and Debian.
  useradd --comment "System user to run solr daemon." --home-dir %{solr_install_link} --system -M --shell /usr/sbin/nologin --user-group %{solr_user}
fi

%post
# Make a symlink to installed version so that upgrades are easier
[ -h "%{solr_install_link}" ] && unlink %{solr_install_link}
ln -sT %{solr_install_dir} %{solr_install_link}

# just enable the service, don't start it.
# If the package is used in enterprise environment, changes will likely need to be made before starting the service.
# (Debian and CentOS have systemctl in different locations.)
systemctl daemon-reload
systemctl enable %{solr_service}

%preun
# Stop the service regardless of whether we are upgrading or uninstalling.
# Issuing stop irrespective of whether service is running or not is harmless.
echo "Stopping %{solr_service}."
systemctl stop %{solr_service}
# Remove symlink to current installation if it exists.
[ -h "%{solr_install_link}" ] && unlink %{solr_install_link}

# Backup previous settings if we are upgrading.
if [ "$1" -gt 0 ]; then
  # Backup setting in default dir
  echo "Backing up %{solr_env_dir}/solr.in.sh"
  [ -f %{solr_env_dir}/solr.in.sh ] && mv %{solr_env_dir}/solr.in.sh %{solr_env_dir}/solr.in.sh.%{solr_backup_str}
  # Backup /etc/solr config
  echo "Backing up %{solr_config_dir}"
  [ -d %{solr_config_dir} ] && mv %{solr_config_dir} %{solr_config_dir}.%{solr_backup_str}
  # Backup SystemD config as this release might be updating something in that.
  if [ -f "%{solr_service_dir}/%{solr_service}" ]; then
    echo "Backing up %{solr_service_dir}/%{solr_service}"
    mv %{solr_service_dir}/%{solr_service} %{solr_service_dir}/%{solr_service}.%{solr_backup_str}
    systemctl daemon-reload
  fi
fi
exit 0

%postun
if [ "$1" == 0 ]; then
    # if this is uninstallation as opposed to upgrade, delete the service
    systemctl disable %{solr_service}
    for dir in %{solr_install_dir} %{solr_log_dir} %{solr_run_dir} %{solr_data_dir} %{solr_config_dir} %{solr_bin_dir} %{solr_env_dir}/solr.in.sh %{solr_service_dir}/%{solr_service}
    do
      echo "Removing $dir"
      rm -rf $dir
    done
    # delete the user
    userdel %{solr_user}
    # Reload systemctl daemon
    systemctl daemon-reload
fi
exit 0

%clean
%__rm -rf "%{buildroot}"

%files -f %{packaged_files}
%defattr(-,%{solr_user},-)
# No need to mention config files as we handle them in upgrades explicitly.

%changelog

* Wed Feb 15 2017 talk@devghai.com
- Packaging for CentOS
- Solr changes (v4.0.0 & above): http://archive.apache.org/dist/lucene/solr/%{solr_version}/changes/Changes.html

* Wed Aug 26 2015 jks@sagevoice.com
- Inital version
