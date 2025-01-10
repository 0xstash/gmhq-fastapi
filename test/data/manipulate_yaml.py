import yaml


def load_workflow_yaml(yaml_path):
    with open(yaml_path, "r") as file:
        return yaml.safe_load(file)


# Load the YAML file
workflow_data = load_workflow_yaml("test/data/parse_yaml.yaml")

# Example: Access the required inputs
required_inputs = workflow_data["required_inputs"]
for input_def in required_inputs:
    print(f"Input name: {input_def['name']}")
    print(f"Description: {input_def['description']}")

# Example: Access workflow steps
workflow_steps = workflow_data["workflow_steps"]
for step in workflow_steps:
    print(f"Step {step['step_number']}: {step['instruction']}")
    print(f"Outputs to: {step['output_variable_name']}")
