from psh.pipeline.builder import PipelineBuilder
from psh.shell import Shell


def test_pipeline_run_with_validation():
    shell = Shell(norc=True)
    builder = PipelineBuilder(shell)
    pipeline = builder.build(enable_validation=True)

    exit_code, report = pipeline.run('true')

    assert exit_code == 0
    assert report is not None
    assert not report.has_errors()


def test_pipeline_run_without_validation():
    shell = Shell(norc=True)
    builder = PipelineBuilder(shell)
    pipeline = builder.build(enable_validation=False)

    exit_code, report = pipeline.run('echo hello', validate=False)

    assert exit_code == 0
    assert report is None
