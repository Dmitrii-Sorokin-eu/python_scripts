# keyvault_sync Script

The `keyvault_sync` script is a versatile Python utility for managing secrets in Azure Key Vaults. It provides several functionalities, including synchronizing secrets between Key Vaults, listing available Key Vaults, and comparing secrets between Key Vaults.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [Synchronize Secrets](#synchronize-secrets)
  - [List Available Key Vaults](#list-available-key-vaults)
  - [Show Differences Between Secrets](#show-differences-between-secrets)
- [Dependencies](#dependencies)
- [Contributing](#contributing)
- [License](#license)

## Prerequisites

- Python 3.x
- Azure subscription and access to Azure Key Vaults

## Installation

1. Clone or download this repository.

2. Install the required dependencies using the following command:

   ```bash
   pip install -r requirements.txt

## Usage
Synchronize Secrets
The script provides the capability to synchronize secrets from a source Key Vault to one or more target Key Vaults. It also supports optional replacement of existing secrets.
```bash
python keyvault_sync.py sync --source-keyvault SOURCE_KEYVAULT_URI --target-keyvaults TARGET_KEYVAULT_URI [TARGET_KEYVAULT_URI ...] --replace-if-exist
Replace SOURCE_KEYVAULT_URI with the URI of the source Key Vault and TARGET_KEYVAULT_URI with the URIs of the target Key Vaults. You can specify multiple target Key Vaults separated by space.


## List Available Key Vaults
To list the available Key Vaults in your Azure subscription:
```bash
python keyvault_sync.py list-keyvaults

## Show Differences Between Secrets
To compare secrets between the source and target Key Vaults and display the differences:
```bash
python keyvault_sync.py list-keyvaults

## Show Differences Between Secrets
To compare secrets between the source and target Key Vaults and display the differences:
```bash
python keyvault_sync.py show-diffs --source-keyvault SOURCE_KEYVAULT_URI --target-keyvaults TARGET_KEYVAULT_URI [TARGET_KEYVAULT_URI ...]

Replace placeholders like SOURCE_KEYVAULT_URI and TARGET_KEYVAULT_URI with actual Key Vault URLs.

## Dependencies
Azure SDK for Python (azure-identity and azure-keyvault-secrets)
tqdm
prettytable
