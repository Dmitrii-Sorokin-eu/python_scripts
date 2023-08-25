import argparse
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from tqdm import tqdm

def sync_secrets(source_kv_uri, target_kv_uris, replace_if_exist):
    source_credential = DefaultAzureCredential()
    source_client = SecretClient(vault_url=source_kv_uri, credential=source_credential)
    
    target_credentials = [DefaultAzureCredential() for _ in target_kv_uris]
    target_clients = [SecretClient(vault_url=target_kv_uri, credential=credential) for target_kv_uri, credential in zip(target_kv_uris, target_credentials)]
    
    source_secrets = source_client.list_properties_of_secrets()
    
    for secret in tqdm(source_secrets, desc="Synchronizing secrets"):
        secret_name = secret.name
        secret_value = source_client.get_secret(secret_name).value
        
        for target_client in target_clients:
            existing_secret = target_client.get_secret(secret_name, None)
            if existing_secret and not replace_if_exist:
                tqdm.write(f"Secret '{secret_name}' already exists in the target Key Vault. Skipping.")
            else:
                target_client.set_secret(secret_name, secret_value)
                tqdm.write(f"Secret '{secret_name}' successfully synchronized to the target Key Vault.")

def list_keyvaults():
    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url="https://<your-keyvault-name>.vault.azure.net/", credential=credential)
    keyvaults = secret_client.list_properties_of_secrets()
    
    for keyvault in keyvaults:
        print(keyvault.id)
            
def main():
    parser = argparse.ArgumentParser(description="Synchronize secrets between Azure Key Vaults or list available Key Vaults.")
    subparsers = parser.add_subparsers(dest="command")

    parser_sync = subparsers.add_parser("sync", help="Synchronize secrets between Key Vaults")
    parser_sync.add_argument("--source-keyvault", required=True, help="Source Key Vault URI")
    parser_sync.add_argument("--target-keyvaults", required=True, nargs="+", help="Target Key Vault URIs (separated by space)")
    parser_sync.add_argument("--replace-if-exist", action="store_true", help="Replace secrets if they already exist in target Key Vaults")

    parser_list = subparsers.add_parser("list-keyvaults", help="List available Key Vaults")

    args = parser.parse_args()

    if args.command == "sync":
        sync_secrets(args.source_keyvault, args.target_keyvaults, args.replace_if_exist)
    elif args.command == "list-keyvaults":
        list_keyvaults()
    else:
        print("Invalid command. Use 'sync' or 'list-keyvaults'.")

if __name__ == "__main__":
    main()
