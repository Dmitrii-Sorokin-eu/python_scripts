import argparse
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ResourceNotFoundError
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.keyvault import KeyVaultManagementClient
from concurrent.futures import ThreadPoolExecutor, as_completed
from prettytable import PrettyTable
from tqdm import tqdm
import concurrent.futures

def get_secret_client(vault_url):
    return SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())

def print_table(field_names, rows, title):
    x = PrettyTable()
    x.field_names = field_names
    for field in field_names:
        x.align[field] = "l"
    for row in rows:
        x.add_row(row)
    print(title)
    print(x)

def process_vault(vault, subscription_id):
    return (vault.properties.vault_uri, vault.id.split("/")[4], subscription_id)

def process_subscription(subscription, specified_subs=None, resource_groups=None):
    results = []
    if specified_subs is not None and subscription.subscription_id not in specified_subs:
        return results

    try:
        credential = DefaultAzureCredential()
        keyvault_client = KeyVaultManagementClient(credential, subscription.subscription_id)
        
        vaults = keyvault_client.vaults.list_by_subscription()
        if resource_groups is not None:
            vaults = [vault for vault in vaults if vault.id.split("/")[4] in resource_groups]
        
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(process_vault, vault, subscription.subscription_id): vault for vault in vaults}
            for future in as_completed(futures):
                results.append(future.result())
                
    except Exception as e:
        pass

    return results

def list_keyvaults(subscription_ids=None, resource_groups=None):
    rows = []
    credential = DefaultAzureCredential()
    subscription_client = SubscriptionClient(credential)
    total_subscriptions = [s for s in subscription_client.subscriptions.list()]
    total_subscriptions_count = len(total_subscriptions)

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_subscription, subscription, subscription_ids, resource_groups): subscription for subscription in total_subscriptions}
        
        for future in tqdm(as_completed(futures), total=total_subscriptions_count, desc="Processing Subscriptions"):
            for vault_uri, resource_group, sub_id in future.result():
                rows.append([vault_uri, resource_group, sub_id])

    print_table(["Keyvault URI", "Resource Group", "Subscription ID"], rows, "Listing Key Vaults")

def sync_single_secret(secret_name, secret_value, target_client, replace_if_exist):
    status = ''
    try:
        target_secret = target_client.get_secret(secret_name)
        if replace_if_exist:
            target_client.set_secret(secret_name, secret_value)
            status = 'REPLACED'
        else:
            status = 'EXIST'
    except ResourceNotFoundError:
        target_client.set_secret(secret_name, secret_value)
        status = 'SYNCED'
    except Exception as e:
        status = f"Error: {e}"
        
    return secret_name, target_client.vault_url.split("//")[-1].split(".")[0], status

def sync_secrets(source_client, target_clients, replace_if_exist=False):
    rows = []
    with ThreadPoolExecutor() as executor:
        future_to_result = {}
        for secret_properties in source_client.list_properties_of_secrets():
            secret_name = secret_properties.name
            secret_value = source_client.get_secret(secret_name).value
            for target_client in target_clients:
                future = executor.submit(sync_single_secret, secret_name, secret_value, target_client, replace_if_exist)
                future_to_result[future] = secret_name
                
        for future in tqdm(as_completed(future_to_result), total=len(future_to_result), desc="Syncing secrets"):
            secret_name, keyvault_name, status = future.result()
            rows.append([secret_name, keyvault_name, status])

    print_table(["Secret Name (source)", "Keyvault Name(s)", "Status"], rows, "Syncing Secrets")
    
def compare_secret(source_client, secret_name, target_clients):
    source_secret = source_client.get_secret(secret_name).value
    diffs = []
    for target_client in target_clients:
        try:
            target_secret = target_client.get_secret(secret_name).value
            diffs.append("MATCH" if source_secret == target_secret else "DIFF")
        except ResourceNotFoundError:
            diffs.append("NOT FOUND")
        except Exception as e:
            diffs.append(f"Error: {e}")
    return diffs

def show_diffs(source_keyvault_uri, target_keyvault_uris):
    # print(f"Source Key Vault: {source_keyvault_uri}")  
    # print(f"Target Key Vaults: {target_keyvault_uris}")  
    
    source_client = SecretClient(vault_url=source_keyvault_uri, credential=DefaultAzureCredential())
    target_clients = [SecretClient(vault_url=url, credential=DefaultAzureCredential()) for url in target_keyvault_uris]
    
    x = PrettyTable()
    x.field_names = ["Secret Name (source)"] + [url.split("//")[-1].split(".")[0] for url in target_keyvault_uris]
    
    for field in x.field_names:
        x.align[field] = "l"
    
    secret_names = [secret_item.name for secret_item in source_client.list_properties_of_secrets()]
    # print(f"Found secret names: {secret_names}")  
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_secret = {executor.submit(compare_secret, source_client, secret_name, target_clients): secret_name for secret_name in secret_names}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_secret), total=len(future_to_secret), desc="Comparing secrets"):
            secret_name = future_to_secret[future]
            result = future.result()
            x.add_row([f"{secret_name}"] + result)
    
    print(x)

def main():
    parser = argparse.ArgumentParser(description="This script provides functionalities for managing Azure Key Vaults including synchronization of secrets, listing Key Vaults, and comparing secrets across multiple Key Vaults.")

    # Main command options
    parser.add_argument("command", choices=["sync", "list-keyvaults", "show-diffs"], 
                        help="The command to execute. Choices are 'sync' to synchronize secrets, 'list-keyvaults' to list all accessible Key Vaults, and 'show-diffs' to compare secrets across Key Vaults.")

    # Arguments for sync command
    parser.add_argument("--source-keyvault", required=False,
                        help="The URI of the source Azure Key Vault. Required for 'sync' and 'show-diffs' commands.")
    parser.add_argument("--target-keyvaults", nargs="+", required=False,
                        help="A list of URIs for the target Azure Key Vaults. Required for 'sync' and 'show-diffs' commands.")
    parser.add_argument("--replace-if-exist", action="store_true", 
                        help="If set, this flag will replace the secret in the target Key Vault(s) if it already exists. Only applicable for 'sync' command.")

    # Arguments for list-keyvaults command
    parser.add_argument("--subscriptions", nargs="+", required=False,
                        help="A list of subscription IDs to filter the Azure Key Vaults by. If not provided, all accessible subscriptions will be used.")
    parser.add_argument("--resource-groups", nargs="+", required=False,
                        help="A list of resource group names to filter the Azure Key Vaults by. If not provided, all accessible resource groups will be used.")

    args = parser.parse_args()

    if args.command == "sync":
        if not args.source_keyvault or not args.target_keyvaults:
            print("The --source-keyvault and --target-keyvaults arguments are required for 'sync' command.")
            return

        source_client = get_secret_client(args.source_keyvault)
        target_clients = [get_secret_client(url) for url in args.target_keyvaults]
        sync_secrets(source_client, target_clients, args.replace_if_exist)

    elif args.command == "list-keyvaults":
        list_keyvaults(subscription_ids=args.subscriptions, resource_groups=args.resource_groups)

    elif args.command == "show-diffs":
        if not args.source_keyvault or not args.target_keyvaults:
            print("The --source-keyvault and --target-keyvaults arguments are required for 'show-diffs' command.")
            return
            
        show_diffs(args.source_keyvault, args.target_keyvaults)

if __name__ == "__main__":
    main()