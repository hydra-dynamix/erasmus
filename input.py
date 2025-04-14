"""This is a module docstring"""


def foo():
    """Function docstring"""
    print("hello")


class Bar:
    """Class docstring"""

    def method(self):
        """Method docstring"""
        return "world"

    def function():
        """Function docstring"""

        def nested_function():
            """Nested function docstring"""
            print("hello")

    try:
        function()
    except Exception as e:
        print(e)
