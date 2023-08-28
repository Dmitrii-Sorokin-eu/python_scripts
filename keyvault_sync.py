import argparse
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ResourceNotFoundError
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.keyvault import KeyVaultManagementClient
from azure.mgmt.resource import ResourceManagementClient
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor, as_completed
from prettytable import PrettyTable
import concurrent.futures
from tqdm import tqdm

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
        print(f"Skipping due to error for Subscription ID {subscription.subscription_id}: {e}")

    return results

def list_keyvaults(subscription_ids=None, resource_groups=None):
    credential = DefaultAzureCredential()
    subscription_client = SubscriptionClient(credential)

    print("Listing Key Vaults accessible to you:\n")

    x = PrettyTable()
    x.field_names = ["Keyvault URI", "Resource Group", "Subscription ID"]
    x.align = "l"

    total_subscriptions = [s for s in subscription_client.subscriptions.list()]
    total_subscriptions_count = len(total_subscriptions)

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_subscription, subscription, subscription_ids, resource_groups): subscription for subscription in total_subscriptions}
        
        for future in tqdm(as_completed(futures), total=total_subscriptions_count, desc="Processing Subscriptions"):
            for vault_uri, resource_group, sub_id in future.result():
                x.add_row([vault_uri, resource_group, sub_id])

    print(x)

def sync_single_secret(secret_name, secret_value, target_client, replace_if_exist):
    status = ''
    try:
        target_secret = target_client.get_secret(secret_name)
        if replace_if_exist:
            target_client.set_secret(secret_name, secret_value)
            status = 'YES, YES'
        else:
            status = 'EXIST'
    except ResourceNotFoundError:
        target_client.set_secret(secret_name, secret_value)
        status = 'YES, NO'
    except Exception as e:
        status = f"Error: {e}"
        
    return secret_name, target_client.vault_url.split("//")[-1].split(".")[0], status

def sync_secrets(source_client, target_clients, replace_if_exist=False):
    x = PrettyTable()
    x.field_names = ["Secret Name (source)", "Keyvault Name(s)", "Status"]
    x.align = "l"

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
            x.add_row([secret_name, keyvault_name, status])

    print(x)

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
    parser.add_argument("--subscriptions", nargs="+", required=False, help="IDs of the subscriptions to scan. If not provided, scans all accessible subscriptions.")
    parser.add_argument("--resource-groups", nargs="+", required=False, help="Resource groups to filter by. If not provided, scans all accessible resource groups.")
    
    args = parser.parse_args()

    if args.command == "sync":
        source_client = SecretClient(vault_url=args.source_keyvault, credential=DefaultAzureCredential())
        target_clients = [SecretClient(vault_url=url, credential=DefaultAzureCredential()) for url in args.target_keyvaults]
        sync_secrets(source_client, target_clients, args.replace_if_exist)
    elif args.command == "list-keyvaults":
        list_keyvaults(subscription_ids=args.subscriptions, resource_groups=args.resource_groups)
    elif args.command == "show-diffs":
        show_diffs(args.source_keyvault, args.target_keyvaults)

if __name__ == "__main__":
    main()
