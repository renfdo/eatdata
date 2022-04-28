# Ingest Framework

Ingest Framework é um modulo em Python que tem como objetivo facilitar a ingestão e limpeza de dados em camadas de Data Lake.
A API permite o crescimento tanto da quantidade de origens de dados como a quantidade de transformações.

## Funcionamento
Através de um arquivo JSON com informações inicial dos dados de origem, o script irá executar a carga para a camada RAW no formato parquet armazenando o arquivo em lotes através da data de importação.
```
RAW\SYSTEM\SUBJECT\TABLE
    \DT_IMPORT=20200101
    \DT_IMPORT=20200102
    \DT_IMPORT=20200103
```

Em seguida o dado será disponibilizado na camada Trusted. Nessa etapa, através do próprio JSON será feito a limpeza do dado através das transformações pré definidas e a armazenamento do dado nessa camada poderá ser feito usando o Upsert que garante que nessa etapa não exista dado duplicado.

## Configuração inicial 
Na pasta ingesframework/config.py existe uma "get_layers" que retorna um dicionário com o nome dos buckets para cada camada.

## JSON
Segue exemplo de estutura básica do arquivo json necessário para uso da API.
```
{
		"job_name": "rent",
		"source": {
			"type": "csv",
			"path": "rent",
			"options": {
				"sep": ",",
				"header":"true"
			}
		},
		"destination": {
			"path": "protheus/rent/",
			"table_name": "rent",
			"raw":{
				"database":"mdl_financeiro_raw"
			},
			"trusted":{
				"ingest_type": "Upsert",
				"database":"mdl_financeiro_trusted",
				"key_column": ["ID"],
				"order_column": "DT_IMPORT",
				"transformations":
				[
					{
						"name": "CastDate",
						"parameters":[
							{"column_name":"DATE_RENT", "source_format": "yyyy-MM-dd"}
						]
					},

					{
						"name": "RenameCast",
						"parameters":[
							{"column_name":"DATE_RENT", "new_column_name":"DT_RENT", "data_type": "Date"}
						]
					}
				]
			}
		}
	}
```

- **job_name**: Nome do objeto json. Esse atributo que será usado na chamada da API- 
- **source**: Conjunto de informações do dado de origem. 
- **destination**: Contém informações de onde os dados serão armazenados, seja na camada RAW ou na Trusted.


#### source

Conjunto de informações do dado de origem. Os Atributos irão alterar de acordo com o tipo de fonte de dados definido através do atributo ingest_type. Como por exemplo "JDBC", "Parquet" e "CSV". Abaixo alguns exemplos:

##### CSV
Quando o atributo type "csv", o script assume que o dado de origem encontra-se na **landing**  definido no **config.py** e irá concatenar o "path" junto o caminho da lading. Ex: s3://landing/rent/.
- **options**: Trata-se do método options disponível no spark.

```
"source": {
			"type": "csv",
			"path": "rent",
			"options": {
				"sep": ",",
				"header":"true"
			}
        }
```

##### Parquet
Quando o atributo type "parquet", o script assume que o dado de origem encontra-se na **landing**  definido no **config.py** e irá concatenar o "path" junto o caminho da lading. Ex: s3://landing/rent/.
- **options**: Também está disponível dentro da opção "parquet"

```
"source": {
	"type": "parquet",
	"path": "testeparquet/"
}
```

##### JDBC
Ao contrário do parquet e csv, o JDBC já não utiliza a lading como origem do dados, pois o JDBC é capaz de buscar direto da origem.
- **options**: Trata-se do método options disponível no spark.
- **dbtype**: Tipo da conexão JDBC, no exemplo é o SQL Server
- **secret_name**: Nome da chave onde encontra-se informações de conexão do banco. Usuário, senha, servidor e porta.
- **driver**: Nome do driver jdbc

```
"source": {
			"type": "jdbc",
			"dbtype":"sqlserver",
			"secret_name": "secret-sqlserver-dadosadv-financeiro",
			"table":"SD2010",
			"driver":"com.microsoft.sqlserver.jdbc.SQLServerDriver",
			"options":{
				"batchsize":"100000",
				"fetchsize":"100000"
			}
		}
```

## Destination

Trata-se de informações ao armazenar os dado na camada RAW e Trusted.

```
"destination": {
			"path": "protheus/SD2010/",
			"table_name": "SD2010",
			
			"raw":{
				"database":"cdl_financeiro_raw"
			},
			"trusted":{
				"ingest_type": "Full",
				"database":"cdl_financeiro_trusted",
				"key_column": ["id"],
				"order_column": ["DT_IMPORT"]
			}
		}
```

- **path**: destino do atributo dentro do lake, essa informação será concatenada com a raw e trusted.
- **raw**: dentro do raw, apenas existe o nome do database, caso não tenha essa informação os arquivos apenas serão salvos no nos destinos e não serão armazenadas tabels on Glue/Hive. Durante o processo, o script vai obter os dados da origem/landing, irá gerar a coluna DT_IMPORT e salvar no formato parquet.

### Trusted

Esssa camada possui duas etapas. A primeira, onde pode ser feito algumas transformações nas colunas, e a segunda onde será escolhido a forma de armazenamento das informações.

```
"trusted":{
				"ingest_type": "Replace",
				"database":"mdl_financeiro_trusted",
				"key_column": ["ID"],
				"partitions":["DATA_SISTEMA"],
				"order_column": "DT_IMPORT",
				"transformations":
				[
				    ***** transformations *****
				]
			}
		}
```

##### ingest_type
Modo como será armazenado o dado na trusted. Existe três opções.
- **Replace**: Carga full, irá sempre sobrescrever todo o dado atual da Trusted substituindo pelo último lote armazenado na RAW.
- **ReplacePartition**: Sobreescreve apenas as partições informadas no atributo "partitions". É uma forma simples de carga incremental.
- **Upsert**: Utiliza o **Apache Hudi**, para fazer o merge do dado e, de acordo com as chaves informadas na "key_column", e através do atributo "order_column" mantem o dado mais recente na camada trusted.
- 

#### Transformation

Aqui existe algumas funções simples de transformação do dado que serão enriquecidas durante a evolução da API. No momento existe as funções abaixo:

- CastData: Converte as colunas informadas passando o formtado em que o dado vem na origem.
- RenameCast: Renomeia as colunas e em seguida aplica a conversão do dado para os data types disponíveis no Spark.


```
"transformations":
	[
		{
			"name": "CastDate",
			"parameters":[
				{"column_name":"DATE_RENT", "source_format": "yyyy-MM-dd"}
			]
		},

		{
			"name": "RenameCast",
			"parameters":[
				{"column_name":"ID", "new_column_name":"ID_TEST", "data_type": "Integer"},
				{"column_name":"DATE_RENT", "new_column_name":"DATE_RENT", "data_type": "Date"}
			]
		}
	]
```