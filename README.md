To enable data-collector pass data-collector.yaml
YAML format:
```yaml
    data_collector_base_directory: "<base directory for data collection>"
    collect_data_function: "<import path for data collection method>"
    collect_pod_logs: true|false # bool whether to collect logs if resource is a pod
```
YAML Example `ocp_utilities/data-collector.yaml`:
```yaml
    data_collector_base_directory: "collected-info"
    collect_data_function: "data_collector.collect_data"
    collect_pod_logs: true
```
Either export path to yaml file in `OPENSHIFT_PYTHON_WRAPPER_DATA_COLLECTOR_YAML` or set `data_collector` in your py_config
The environment variable takes precedence over py_config.

To use dynamic base directory, export `OPENSHIFT_PYTHON_WRAPPER_DATA_COLLECTOR_DYNAMIC_BASE_DIR`  
Example:
```
data_collector_base_directory = "/data/results/collected-info"
OPENSHIFT_PYTHON_WRAPPER_DATA_COLLECTOR_DYNAMIC_BASE_DIR = "dynamic_collector_test_dir"

Result: /data/results/dynamic_collector_test_dir/collected-info
```
