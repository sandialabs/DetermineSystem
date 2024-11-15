from pathlib import Path
import pytest
import re
import sys
from unittest.mock import patch

root_dir = (Path.cwd()/".."
            if (Path.cwd()/"conftest.py").exists()
            else Path.cwd())

sys.path.append(str(root_dir))
from determinesystem import DetermineSystem


@pytest.fixture
def supported_systems_file():
    return "test_supported_systems.ini"


def test_supported_sys_names_property_returns_correctly(supported_systems_file):
    ds = DetermineSystem("build_name", supported_systems_file)
    systems_in_test_file = ["ats1", "ats2", "cts1", "rhel7", "van1-tx2"]

    assert set(ds.supported_sys_names) == set(systems_in_test_file)


###############################
#  System Name Determination  #
###############################
@pytest.mark.parametrize("data", [
    {"hostname": "mutrino", "sys_name": "ats1"},
    {"hostname": "vortex", "sys_name": "ats2"},
    {"hostname": "eclipse", "sys_name": "cts1"},
    {"hostname": "cee-build007", "sys_name": "rhel7"},
    {"hostname": "cee-compute004", "sys_name": "rhel7"},
    {"hostname": "cee-compute005", "sys_name": "rhel7"},
])
@patch("socket.gethostname")
def test_system_name_determination_correct_for_hostname(
    mock_gethostname, data, supported_systems_file
):
    mock_gethostname.return_value = data["hostname"]
    ds = DetermineSystem("build_name", supported_systems_file)
    assert ds.system_name == data["sys_name"]


@patch("socket.gethostname")
def test_sys_name_in_build_name_not_matching_hostname_raises(
    mock_gethostname, supported_systems_file
):
    mock_gethostname.return_value = "stria"
    ds = DetermineSystem("ats1_build-name", supported_systems_file)
    with pytest.raises(SystemExit) as excinfo:
        ds.system_name
    exc_msg = excinfo.value.args[0]
    for msg in ["Hostname 'stria' matched to system 'van1-tx2'",
                "but you specified 'ats1' in the build name",
                "add the --force flag"]:
        msg = msg.replace(" ", r"\s+\|?\s*")  # account for line breaks
        assert re.search(msg, exc_msg) is not None


@patch("socket.gethostname")
def test_sys_name_in_build_name_overrides_hostname_match_when_forced(
    mock_gethostname, supported_systems_file
):
    mock_gethostname.return_value = "stria"
    ds = DetermineSystem("ats1_build-name", supported_systems_file,
                         force_build_name=True)
    assert ds.system_name == "ats1"


@patch("socket.gethostname")
def test_sys_name_in_build_name_not_bordered_by_underscores_not_recognized(
    mock_gethostname, supported_systems_file
):
    mock_gethostname.return_value = "unsupported_hostname"
    # Should mention double-checking there's an underscore surrounding the
    # system name. Without getting too specific, just check for the word
    # "underscore".
    msg = "underscore"
    with pytest.raises(SystemExit, match=msg):
        ds = DetermineSystem("some-prefix-ats1_build-name", supported_systems_file)
        ds.system_name


@pytest.mark.parametrize("hostname", ["stria", "unsupported_hostname"])
@patch("socket.gethostname")
def test_multiple_sys_names_in_build_name_raises_regardless_of_hostname_match(
    mock_gethostname, hostname, supported_systems_file
):
    mock_gethostname.return_value = hostname
    ds = DetermineSystem("ats1_rhel7_build-name", supported_systems_file)
    with pytest.raises(SystemExit) as excinfo:
        ds.system_name
    exc_msg = excinfo.value.args[0]
    assert ("Cannot specify more than one system name in the build name"
            in exc_msg)
    assert "- ats1" in exc_msg
    assert "- rhel7" in exc_msg


@pytest.mark.parametrize("data", [
    {"build_name": "no-system-here", "sys_name": None, "raises": True, "hostname": "unsupported_hostname"},
    {"build_name": "ats1_build-name", "sys_name": "ats1", "raises": False, "hostname": "mutrino"},
])
@patch("socket.gethostname")
def test_unsupported_hostname_handled_correctly(mock_gethostname, data,
                                                supported_systems_file):
    mock_gethostname.return_value = data["hostname"]
    ds = DetermineSystem(data["build_name"], supported_systems_file)
    if data["raises"]:
        with pytest.raises(SystemExit) as excinfo:
            ds.system_name
        exc_msg = excinfo.value.args[0]
        msg = ("Unable to find valid system name in the build name or for "
               "the hostname 'unsupported_hostname'")
        msg = msg.replace(" ", r"\s+\|?\s*")  # account for line breaks
        assert re.search(msg, exc_msg) is not None
        assert str(ds.supported_systems_file) in exc_msg
    else:
        assert ds.system_name == data["sys_name"]
