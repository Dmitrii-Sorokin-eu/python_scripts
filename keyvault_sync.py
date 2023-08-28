import argparse
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ResourceNotFoundError
from azure.mgmt.resource import SubscriptionClient
from prettytable import PrettyTable
import concurrent.futures
from tqdm import tqdm

def list_keyvaults():
    credential = DefaultAzureCredential()
    keyvault_client = KeyVaultManagementClient(credential)

    print("Listing Key Vaults accessible to you:\n")

    for vault in keyvault_client.vaults.list():
        try:
            SecretClient(vault_url=vault.properties.vault_uri, credential=credential)
            print(f"- {vault.properties.vault_uri}")
        except Exception:
            pass

    print("\n")

def compare_secret(source_client, secret_name, target_clients):
    result = []
    source_secret = source_client.get_secret(secret_name)
    
    for target_client in target_clients:
        try:
            target_secret = target_client.get_secret(secret_name)
            if source_secret.value == target_secret.value:
                result.append("YES/YES")
            else:
                result.append("YES/NO")
        except ResourceNotFoundError:
            result.append("NO/NO")
    
    return result

def show_diffs(source_keyvault_uri, target_keyvault_uris):
    source_client = SecretClient(vault_url=source_keyvault_uri, credential=DefaultAzureCredential())
    target_clients = [SecretClient(vault_url=url, credential=DefaultAzureCredential()) for url in target_keyvault_uris]
    
    x = PrettyTable()
    x.field_names = ["Secret Name (source)"] + [url.split("//")[-1].split(".")[0] for url in target_keyvault_uris]
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        secret_names = [secret_item.name for secret_item in source_client.list_properties_of_secrets()]
        future_to_secret = {executor.submit(compare_secret, source_client, secret_name, target_clients): secret_name for secret_name in secret_names}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_secret), total=len(future_to_secret), desc="Comparing secrets"):
            secret_name = future_to_secret[future]
            result = future.result()
            x.add_row([f"{secret_name}"] + result)
    
    print(x)

def main():
    parser = argparse.ArgumentParser(description="Synchronize secrets between Azure Key Vaults.")
    parser.add_argument("command", choices=["sync", "list-keyvaults", "show-diffs"], help="Specify the command")
    parser.add_argument("--source-keyvault", required=False, help="URI of the source Key Vault")
    parser.add_argument("--target-keyvaults", nargs="+", required=False, help="URIs of the target Key Vaults")
    parser.add_argument("--replace-if-exist", action="store_true", help="Replace secrets in target Key Vaults if they already exist")
    args = parser.parse_args()

    if args.command == "sync":
        source_client = SecretClient(vault_url=args.source_keyvault, credential=DefaultAzureCredential())
        target_clients = [SecretClient(vault_url=url, credential=DefaultAzureCredential()) for url in args.target_keyvaults]
        sync_secrets(source_client, target_clients, args.replace_if_exist)
    elif args.command == "list-keyvaults":
        list_keyvaults()
    elif args.command == "show-diffs":
        show_diffs(args.source_keyvault, args.target_keyvaults)
    # ... (same as before)

if __name__ == "__main__":
    main()