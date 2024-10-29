import csv

class LeadManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.leads = self._load_leads()

    def _load_leads(self):
        leads = []
        with open(self.file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames

            # Si la columna 'Analizado' no existe, se agrega
            if "Analizado" not in fieldnames:
                fieldnames.append("Analizado")
                leads = [row for row in reader]
                for lead in leads:
                    lead["Analizado"] = "No"  # Inicializa como "No" si aún no ha sido analizado
                self._save_leads(leads, fieldnames)
            else:
                for row in reader:
                    leads.append(row)
        return leads

    def get_all_leads(self, limit=None):
        """Obtiene todos los leads o un número limitado de leads si se especifica `limit`."""
        if limit is not None:
            return self.leads[:limit]
        return self.leads
    
    def get_unanalyzed_leads(self, limit=None):
        """Obtiene solo los leads no analizados, hasta el número especificado en `limit`."""
        unanalyzed_leads = [lead for lead in self.leads if lead["Analizado"] == "No"]
        if limit is not None:
            return unanalyzed_leads[:limit]
        return unanalyzed_leads    

    def find_lead_by_mobile(self, mobile):
        """Busca un lead por el número de teléfono móvil."""
        return next((lead for lead in self.leads if lead["Mobile"] == mobile), None)

    def filter_leads_by_status(self, status):
        """Filtra los leads por el estado de lead especificado."""
        return [lead for lead in self.leads if lead["Lead Status"] == status]

    def add_lead(self, lead_data):
        """Agrega un nuevo lead y actualiza el archivo CSV."""
        lead_data["Analizado"] = "No"  # Asume que el nuevo lead aún no ha sido analizado
        self.leads.append(lead_data)
        self._save_leads(self.leads, self.leads[0].keys())

    def update_lead(self, record_id, field, new_value):
        """Actualiza un campo específico de un lead identificado por Record Id."""
        for lead in self.leads:
            if lead["Record Id"] == record_id:
                lead[field] = new_value
                self._save_leads()
                return lead
        return None

    def _save_leads(self):
        """Guarda los datos actuales en el archivo CSV."""
        with open(self.file_path, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = self.leads[0].keys() if self.leads else []
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.leads)

    def marcar_lead_como_analizado(self, record_id):
        """Marca un lead como analizado actualizando el campo 'Analizado' a 'Sí'."""
        return self.update_lead(record_id, "Analizado", "Sí")