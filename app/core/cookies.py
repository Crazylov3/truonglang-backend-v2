from fastapi import Response


def set_cookie(
    response: Response, 
    name: str, 
    value: str, 
    secure: bool = True,
    max_age: int = None,
    httponly: bool = True,
    samesite: str = "strict"
) -> None:
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=httponly,
        secure=secure,
        samesite=samesite,
        path="/"
    )


def clear_cookie(
    response: Response,
    name: str,
    secure: bool = True,
    httponly: bool = True,
    samesite: str = "strict"
) -> None:
    """Clear a cookie."""
    response.delete_cookie(
        key=name,
        path="/",
        httponly=httponly,
        secure=secure,
        samesite=samesite
    )