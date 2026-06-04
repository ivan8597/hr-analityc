from etl.hr.pipeline import HRPipeline
from etl.hr.schema_mapper import HRSchemaMapper


def test_pipeline_run(pg_db, test_excel_file, test_mapping_file, run_id):
    mapper = HRSchemaMapper(test_mapping_file)
    pipeline = HRPipeline(pg_db, mapper, run_id, test_excel_file)
    extracted, loaded, rejected = pipeline.run()

    assert extracted == 4
    assert loaded == 3
    assert rejected == 2

    core_count = pg_db.execute("SELECT COUNT(*) FROM core.hr_employee")
    assert core_count.fetchone()[0] == 3

    staging_count = pg_db.execute(
        "SELECT COUNT(*) FROM staging.hr_raw WHERE run_id = :run_id",
        {"run_id": run_id},
    )
    assert staging_count.fetchone()[0] == 4
