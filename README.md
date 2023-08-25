# keyvault_sync Script

The `keyvault_sync` script is a Python utility that enables synchronization of secrets between Azure Key Vaults. It allows you to copy secrets from a source Key Vault to one or more target Key Vaults, optionally replacing existing secrets in the target Key Vaults.

## Prerequisites

- Python 3.x
- Azure subscription and access to Azure Key Vaults
- Install required dependencies using: `pip install azure-identity azure-keyvault-secrets tqdm`

## Usage

1. Clone or download this repository.

2. Open a terminal and navigate to the directory containing the script.

3. Run the script with the desired parameters:

```bash
python keyvault_sync.py --source-keyvault SOURCE_KEYVAULT_URI --target-keyvaults TARGET_KEYVAULT_URI [TARGET_KEYVAULT_URI ...] --replace-if-exist
