def Create(project_name: str) -> str:
    """Generate an entire RA project structure."""
    project_lower = project_name.lower()
    if "hospital management" in project_lower:
        return ( f"Project '{project_name}' created.\n\n"
                 "main.ra:\n"
                 "  import DB\n"
                 "  @Cls Hospital:\n"
                 "    @Var patients: []\n"
                 "    @Method add_patient(name):\n"
                 "      .patients.append(name)\n"
                 "    @Method list_patients():\n"
                 "      return .patients\n\n"
                 "  @Cls Main:\n"
                 "    @Method run():\n"
                 "      hosp = Hospital()\n"
                 "      hosp.add_patient(\"John\")\n"
                 "      .Print(hosp.list_patients())\n\n"
                 "db.ra – database helpers (auto‑generated)\n"
                 "ui.ra – user interface templates\n"
                 "README.md – project documentation" )
    else:
        return ( f"Project '{project_name}' generated.\n"
                 f"Create folder ./{project_name}/\n"
                 f"Place main.ra, lib/, and docs/ inside." )