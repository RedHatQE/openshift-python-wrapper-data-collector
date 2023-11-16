import logging
import os

import yaml
from ocp_resources.datavolume import DataVolume
from ocp_resources.namespace import Namespace
from ocp_resources.pod import Pod
from ocp_resources.project import ProjectRequest
from ocp_resources.resource import NamespacedResource, get_client
from ocp_resources.virtual_machine import VirtualMachine
from pytest_testconfig import config as py_config

LOGGER = logging.getLogger(__name__)


def collect_vmi_data(vmi, directory, collect_pod_logs=True):
    """
    Collect VMI pod and virt_launcher pod yamls and virt_launcher pod log

    Args:
        vmi (VirtualMachineInstance): vmi instance
        directory (str): output directory
        collect_pod_logs (bool, default=True): collect virt-launcher pod log if True else do not collect log
    """
    collect_pods_data(
        pods_list=[vmi.virt_launcher_pod],
        base_directory=directory,
        collect_pod_logs=collect_pod_logs,
    )
    write_to_file(
        file_name=f"{vmi.name}.yaml",
        content=vmi.instance.to_str(),
        base_directory=directory,
    )


def collect_data_volume_data(dyn_client, directory, collect_pod_logs=True, cdi_pod_prefixes=None):
    """
    Collect DataVolume-related pods (importer/cdi-upload/source-pod) yamls and logs

    Args:
        dyn_client (DynamicClient): K8s client
        directory (str): output directory
        collect_pod_logs (bool, default=True): collect pods logs if True else do not collect logs
        cdi_pod_prefixes (tuple, optional): pod prefix names
    """
    cdi_pod_prefixes = cdi_pod_prefixes or ("importer", "cdi-upload")
    collected_pods = []
    for pod in Pod.get(dyn_client=dyn_client):
        pod_name = pod.name
        if pod_name.startswith(cdi_pod_prefixes) or pod_name.endswith("source-pod"):
            collected_pods.append(pod)

    if collected_pods:
        collect_pods_data(
            pods_list=collected_pods,
            base_directory=directory,
            collect_pod_logs=collect_pod_logs,
        )


def collect_data(directory, resource_object, collect_pod_logs=True):
    """
    Base function to collect resource data

    Args:
        directory (str): output directory
        resource_object (cluster resource): Cluster resource
        collect_pod_logs (bool, default=True): collect pods logs if True else do not collect logs
    """
    LOGGER.info(f"Collecting instance data for {resource_object.kind} {resource_object.name} under {directory}")

    if resource_object.kind == Pod.kind:
        collect_pods_data(
            pods_list=[resource_object],
            collect_pod_logs=collect_pod_logs,
            base_directory=directory,
        )
        return

    if resource_object.kind == ProjectRequest.kind:
        resource_object = Namespace(name=resource_object.name)

    output_directory = os.path.join(
        directory,
        resource_object.kind,
        resource_object.name,
    )

    write_to_file(
        file_name=f"{resource_object.name}.yaml",
        content=resource_object.instance.to_str(),
        base_directory=output_directory,
    )

    if resource_object.kind == VirtualMachine.kind and resource_object.vmi:
        collect_vmi_data(
            vmi=resource_object.vmi,
            directory=output_directory,
            collect_pod_logs=collect_pod_logs,
        )

    if resource_object.kind == DataVolume.kind:
        collect_data_volume_data(
            dyn_client=resource_object.client,
            directory=output_directory,
            collect_pod_logs=collect_pod_logs,
        )


def prepare_pytest_item_data_dir(item, base_directory, subdirectory_name):
    """
    Prepare output directory for pytest item

    "tests_path" must be configured in pytest.ini.

    Args:
        item (pytest item): test invocation item
        base_directory (str): output directory
        subdirectory_name (str):  output directory last subdirectory

    Example:
        item.fspath= "/home/user/git/tests-repo/tests/test_dir/test_something.py"
        datacollector base directory = "collected-info"
        subdirectory_name = "setup"
        item.name = "test1"
        item_dir_log = "collected-info/test_dir/test_something/test1/setup"

    Returns:
        str: output dir full path
    """
    item_cls_name = item.cls.__name__ if item.cls else ""
    tests_path = item.session.config.inicfg.get("testpaths")
    assert tests_path, "pytest.ini must include testpaths"

    fspath_split_str = "/" if tests_path != os.path.split(item.fspath.dirname)[1] else ""
    item_dir_log = os.path.join(
        base_directory,
        item.fspath.dirname.split(f"/{tests_path}{fspath_split_str}")[-1],
        item.fspath.basename.partition(".py")[0],
        item_cls_name,
        item.name,
        subdirectory_name,
    )
    os.makedirs(item_dir_log, exist_ok=True)
    return item_dir_log


def collect_resources_yaml_instance(resources_to_collect, base_directory, namespace_name=None):
    """
    Collect resources instances yamls.

    Get cluster resources based on resource kinds passed in resources_to_collect.

    Args:
        resources_to_collect (list): Resources classes
        base_directory (str): output directory
        namespace_name (str): namespace name
    """
    for _resources in resources_to_collect:
        try:
            get_kwargs = {"dyn_client": get_client()}
            if isinstance(_resources, NamespacedResource):
                get_kwargs["namespace"] = namespace_name

            for resource_obj in _resources.get(**get_kwargs):
                try:
                    write_to_file(
                        file_name=f"{resource_obj.name}.yaml",
                        content=resource_obj.instance.to_str(),
                        base_directory=base_directory,
                        extra_dir_name=resource_obj.kind,
                    )
                except Exception as exp:
                    LOGGER.warning(f"Failed to collect resource: {resource_obj.kind} {resource_obj.name} {exp}")
        except Exception as exp:
            LOGGER.warning(f"Failed to collect resources for type: {_resources} {exp}")


def collect_pods_data(pods_list, base_directory, collect_pod_logs=True):
    """
    Collect pods yamls and containers logs

    Args:
        pods_list (list): list of cluster pods resources
        base_directory(str): output directory
        collect_pod_logs (bool, default=True): collect virt-launcher pod log if True else do not collect log
    """
    output_directory = os.path.join(base_directory, Pod.kind)
    for pod in pods_list:
        pod_output_dir = os.path.join(output_directory, pod.name)
        try:
            write_to_file(
                file_name=f"{pod.name}.yaml",
                content=pod.instance.to_str(),
                base_directory=pod_output_dir,
            )
        except Exception as exp:
            LOGGER.warning(f"Failed to collect pod {pod.name} yaml: {exp}")

        if collect_pod_logs:
            write_container_logs_to_files(pod=pod, base_directory=pod_output_dir)


def write_to_file(file_name, content, base_directory, extra_dir_name=None, mode="w"):
    """
    Write to a file that will be available after the run execution.

    Args:
        file_name (str): name of the file to write.
        content (str): the content of the file to write.
        base_directory (str): the base directory to write the file
        extra_dir_name (str, optional): directory name to create inside base_directory.
        mode (str, optional): specifies the mode in which the file is opened.
    """
    os.makedirs(base_directory, exist_ok=True)
    file_path = os.path.join(base_directory, file_name)
    if extra_dir_name:
        extras_dir = os.path.join(base_directory, extra_dir_name)
        os.makedirs(extras_dir, exist_ok=True)
        file_path = os.path.join(extras_dir, file_name)

    try:
        with open(file_path, mode) as fd:
            fd.write(content)
    except Exception as exp:
        LOGGER.warning(f"Failed to write extras to file: {file_path} {exp}")


def write_container_logs_to_files(pod, base_directory):
    """
    Write pod's containers logs to base_directory/containers directory.

    Args:
        pod (Pod): cluster pod resource
        base_directory (str): output directory
    """
    try:
        containers_list = [container["name"] for container in pod.instance.status.containerStatuses]
    except Exception as exp:
        LOGGER.warning(f"Failed to get pod {pod.name} containers: {exp}")
        return

    for container in containers_list:
        try:
            write_to_file(
                file_name=f"{pod.name}_{container}.log",
                content=pod.log(**{"container": container}),
                base_directory=base_directory,
                extra_dir_name="containers",
            )
        except Exception as exp:
            LOGGER.warning(f"Failed to collect pod {pod.name} container {container} logs: {exp}")


def get_data_collector_base_dir(data_collector_dict):
    """
    Get data collector base directory.

    If `collector_directory` is set in data_collector_dict, it will be used instead of `data_collector_base_directory`
    If `OPENSHIFT_PYTHON_WRAPPER_DATA_COLLECTOR_DYNAMIC_BASE_DIR` is set, add its value to base directory path.
    For example:
        data_collector_base_directory = "/data/results/collected-info"
        OPENSHIFT_PYTHON_WRAPPER_DATA_COLLECTOR_DYNAMIC_BASE_DIR = "product_a"
        Output directory: /data/results/product_a/collected-info

    Args:
        data_collector_dict (dict): data collector config dict

    Returns:
        str: data collector target directory

    """
    data_collector_directory = data_collector_dict.get(
        "collector_directory",
        data_collector_dict["data_collector_base_directory"],
    )
    data_collect_dynamic_dir = os.environ.get("OPENSHIFT_PYTHON_WRAPPER_DATA_COLLECTOR_DYNAMIC_BASE_DIR")
    if data_collect_dynamic_dir:
        path_head, path_tail = os.path.split(data_collector_directory.rstrip("/"))
        data_collector_directory = os.path.join(path_head, data_collect_dynamic_dir, path_tail)

    return data_collector_directory


def get_data_collector_dict():
    """
    Get data collector config from environment variable `OPENSHIFT_PYTHON_WRAPPER_DATA_COLLECTOR_YAML`, yaml or pyconfig

    Returns:
        dict: data collector configuration
    """
    data_collect_env_var_yaml = os.environ.get("OPENSHIFT_PYTHON_WRAPPER_DATA_COLLECTOR_YAML")
    if data_collect_env_var_yaml:
        try:
            with open(data_collect_env_var_yaml, "r") as fd:
                return yaml.safe_load(fd.read())
        except FileNotFoundError:
            LOGGER.error(f"Failed to open {data_collect_env_var_yaml} file")
    else:
        try:
            return py_config.get("data_collector")
        except ImportError:
            LOGGER.error("Failed to get py_config 'data_collector' config")
