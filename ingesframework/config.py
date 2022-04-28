

def get_layers(account, env, domain):
    storage_layers_s3 = {
        "artifact":
            {
                'path': f's3://multlake-{account}-{domain}-{env}-artifact/'
            },
        "landing":
            {
                'path': f's3://multlake-{account}-{domain}-{env}-landing/'
            },
        
        "raw":
            {
                'path': f's3://multlake-{account}-{domain}-{env}-raw/'
            },
        "trusted":
            {
                'path': f's3://multlake-{account}-{domain}-{env}-trusted/'
            }
    }
    
    return storage_layers_s3

# falta implementar
always_lading = True