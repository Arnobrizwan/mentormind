from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Stock page-number pagination, but clients may request larger pages
    (the studio asks for page_size=100 on flashcards/questions/tickets).
    Bounded so nobody can demand the whole table in one response."""

    page_size_query_param = "page_size"
    max_page_size = 200
