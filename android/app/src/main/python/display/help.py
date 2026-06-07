"""Help system for the RA Language interpreter."""

HELP_TEXT = """

# RA Syntax Reference

Variables:
I name=<int>          Integer variable
S name=<string>       String variable
L name=<list>         List variable (under development)
name=<expr>           Reassign variable

Print:
p."text"              Print text
p.variable            Print variable
p.obj.property        Print object property

Methods:
M.Name:               Define method
...
/.close               Close method

Name.run              Execute global method
Obj.Method.run        Execute object method

Classes:
@Cls.Name:            Define class
...
@.close               Close class

Objects:
Obj.Class.Object      Create object

OOP:
OOP                   Activate OOP library

Constructor:
Con:
...
Con.close

Encapsulation:
En:
...
En.close

Example:

@Cls.Person:

  Con:
      p."Created"
  Con.close

  En:
      S password="1234"
  En.close

  S name="Ken"

@.close

Obj.Person.Ken

Database:
Db.Name:
...
Db.close

Db.Name.save
Db.Name.load

Check (Exception Handling):
Check:
...
Valid:
...
Invalid:
...
Check.close

Example:

Check:

  p.UnknownVariable

Valid:

  p."Success"

Invalid:

  p."Failed"

Check.close

Switch Case:
Key.variable:

  c.value:
      ...

  def:
      ...

Key.close

Example:

Key.age:

  c.18:
      p."Adult"

  def:
      p."Unknown"

Key.close

Object Property Switch:

Key.Admin.role:

  c."Admin":
      ...

  def:
      ...

Key.close

Loops:
? For.i=start;end,

  ...

#

? While.condition,

  ...

#

Conditions:
! If.condition,

  ...

#

!! condition,

  ...

#

! Else

  ...

#

Blocks:
.run:
...
r.close

.fun:
...
f.close

PF (Program Framework):
PF                    Activate PF framework

Program Handler:

pH:

  M.Login
  M.Dashboard

pH.close

Single Function Flow:

fF:

  User.Login

f.close

Multiple Function Flows:

fF.M.Login:

  User.Login

f.close

fF.M.Dashboard:

  User.Dashboard

f.close

PF + Check:

fF.M.Login:

  Check:

      User.Login

  Valid:

      User.Dashboard

  Invalid:

      User.Login

  Check.close

f.close

PF + Key:

fF.M.Admin:

  Key.Admin.role:

      c."Admin":
          User.Admin

      def:
          User.Guest

  Key.close

f.close

Other:
p.expression          Print expression
R.expression          Return value

Libraries:
OOP                   Object Oriented Programming
PF                    Program Framework

Commands:
help                  Show help
clear                 Clear screen
reset                 Restart runtime
exit                  Exit RA

Version:
RA Language v1.0.3

Features:
✓ Variables
✓ Methods
✓ Classes
✓ Objects
✓ Constructors
✓ Encapsulation
✓ Database
✓ Check
✓ Key
✓ OOP
✓ PF Framework
"""


def show_help() -> None:
    """Print the RA syntax reference."""
    print(HELP_TEXT)
