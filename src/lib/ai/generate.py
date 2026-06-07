def Gen(description: str) -> str:
    """Generate RA code from natural language description."""
    desc_lower = description.lower()

    if "student class" in desc_lower:
        return ( "@Cls Student:\n"
                 "  @Var name: str\n"
                 "  @Var age: int\n"
                 "  @Method __init__(name, age):\n"
                 "    .name = name\n"
                 "    .age = age\n"
                 "  @Method display():\n"
                 "    .Print(\"Name: \" + .name)\n"
                 "    .Print(\"Age: \" + .age)\n" )
    elif "login class" in desc_lower:
        return ( "@Cls Login:\n"
                 "  @Var username: str\n"
                 "  @Var password: str\n"
                 "  @Method authenticate(uname, pwd):\n"
                 "    return uname == .username and pwd == .password\n" )
    else:
        return ( "@Cls GeneratedClass:\n"
                 "  @Method run():\n"
                 "    .Print(\"RA code generated from: \" + \"{description}\")\n"
                 .format(description=description) )