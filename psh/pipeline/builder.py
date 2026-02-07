"""Factory for building reusable shell processing pipelines."""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..lexer import tokenize
from ..parser import ParserConfig, parse
from ..parser.validation.validation_pipeline import ValidationPipeline, ValidationReport
from ..token_types import Token


@dataclass
class ShellPipeline:
    """Pipeline wrapper that runs tokenize → parse → validate → execute."""

    shell: 'Shell'
    parser_config: Optional[ParserConfig] = None
    strict_lexer: bool = True
    enable_validation: bool = True

    def __post_init__(self):
        self._validator = ValidationPipeline() if self.enable_validation else None

    def tokenize(self, text: str) -> List[Token]:
        return tokenize(text, strict=self.strict_lexer)

    def parse(self, tokens: List[Token]):
        return parse(tokens, config=self.parser_config)

    def validate(self, ast) -> Optional[ValidationReport]:
        if not self._validator:
            return None
        return self._validator.validate(ast)

    def execute(self, ast) -> int:
        return self.shell.execute(ast)

    def run(self, text: str, validate: Optional[bool] = None) -> Tuple[int, Optional[ValidationReport]]:
        tokens = self.tokenize(text)
        ast = self.parse(tokens)

        do_validate = self.enable_validation if validate is None else validate
        report = self.validate(ast) if do_validate else None

        exit_code = self.execute(ast)
        return exit_code, report


class PipelineBuilder:
    """Constructs shell processing pipelines with consistent wiring."""

    def __init__(self, shell: 'Shell'):
        self.shell = shell

    def build(self,
              parser_config: Optional[ParserConfig] = None,
              strict_lexer: bool = True,
              enable_validation: bool = True) -> ShellPipeline:
        return ShellPipeline(
            shell=self.shell,
            parser_config=parser_config,
            strict_lexer=strict_lexer,
            enable_validation=enable_validation,
        )


__all__ = ["PipelineBuilder", "ShellPipeline"]
