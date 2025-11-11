from pupa.importers.bills import BillImporter


class LAMetroBillImporter(BillImporter):

    def get_object(self, bill):
        spec = {
            "identifier": bill["identifier"],
        }
        if "from_organization_id" in bill:
            spec["from_organization_id"] = bill["from_organization_id"]

        return self.model_class.objects.prefetch_related(
            "actions__related_entities",
            "versions__links",
            "documents__links",
        ).get(**spec)
