from linkml.generators import PydanticGenerator
from linkml.generators.pydanticgen import PydanticModule, Imports, PydanticBaseModel
from linkml.generators.pydanticgen.pydanticgen import SplitMode
from linkml_runtime import SchemaView
from linkml_runtime.utils.formatutils import camelcase

class CustomPydanticGenerator(PydanticGenerator):
    """Custom PydanticGenerator that skips default imports"""

    def render(self) -> PydanticModule:
        """
        Override render to skip DEFAULT_IMPORTS
        """
        sv: SchemaView
        sv = self.schemaview

        # Start with empty imports instead of DEFAULT_IMPORTS
        imports = Imports()

        # Add custom imports if provided
        if self.imports is not None:
            if isinstance(self.imports, Imports):
                imports += self.imports
            else:
                for i in self.imports:
                    imports += i
        if self.split_mode == SplitMode.FULL:
            imports += self._get_imports()

        # injected classes - we'll also need to handle this
        # since DEFAULT_INJECTS might include things that depend on DEFAULT_IMPORTS
        injected_classes = []  # Start with empty instead of DEFAULT_INJECTS
        if self.injected_classes is not None:
            injected_classes += self.injected_classes.copy()

        # enums
        enums = self.before_generate_enums(list(sv.all_enums().values()), sv)
        enums = self.generate_enums({e.name: e for e in enums})

        base_model = PydanticBaseModel(extra_fields=self.extra_fields, fields=self.injected_fields)

        # schema classes
        class_results = []
        source_classes, imported_classes = self._get_classes(sv)
        source_classes = self.sort_classes(source_classes, imported_classes)
        # Don't want to generate classes when class_uri is linkml:Any, will
        # just swap in typing.Any instead down below
        source_classes = [c for c in source_classes if c.class_uri != "linkml:Any"]
        source_classes = self.before_generate_classes(source_classes, sv)
        self.sorted_class_names = [camelcase(c.name) for c in source_classes]
        for cls in source_classes:
            cls = self.before_generate_class(cls, sv)
            result = self.generate_class(cls)
            result = self.after_generate_class(result, sv)
            class_results.append(result)
            if result.imports is not None:
                imports += result.imports
            if result.injected_classes is not None:
                injected_classes.extend(result.injected_classes)

        class_results = self.after_generate_classes(class_results, sv)

        classes = {r.cls.name: r.cls for r in class_results}
        injected_classes = self._clean_injected_classes(injected_classes)

        imports.render_sorted = self.sort_imports

        module = PydanticModule(
            metamodel_version=self.schema.metamodel_version,
            version=self.schema.version,
            python_imports=imports,
            base_model=base_model,
            injected_classes=injected_classes,
            enums=enums,
            classes=classes,
        )
        module = self.include_metadata(module, self.schemaview.schema)
        module = self.before_render_template(module, self.schemaview)
        return module
