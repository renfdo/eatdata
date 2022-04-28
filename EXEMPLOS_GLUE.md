
aws glue start-job-run \
        --job-name multlake-teste-ingest-raw \
        --arguments '{
                        "--parametros": "glue_scripts/parametros/200_parametros_protheus.json",
                        "--job":"DA1200",
                        "--isIncremental":"FALSE",
                        "--dtimport":"20220128"
                    }'
					
aws glue start-job-run \
	    --job-name multlake-felipe-ingest-trusted \
	    --arguments '{
						"--parametros": "glue_scripts/parametros/sample.json",
						"--job":"user2",
						"--isIncremental":"FALSE",
						"--dtimport":"20220121"
					}'

