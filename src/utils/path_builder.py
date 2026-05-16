def make_path(module: str, class_name: str, package: str = None, domain: str = None) -> str:
  """
  This method creates a path string for importing a class from a module.

  Parameters:
  ----------------
  module (str): 
    The module path.

  class_name (str): 
    The name of the class.

  package (str): 
    The package name, if applicable.

  domain (str): 
    The domain of the class, if applicable.

  Returns:
  ----------------
  str: 
    The full path string for importing the class.
  """
  path_string = ""
  if package:
    path_string += f"{package}"
    
  if domain:
    path_string += f".{domain}"
  
  path_string += f".{module}:{class_name}"
  return path_string
