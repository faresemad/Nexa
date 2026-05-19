# core/response.py
from rest_framework.response import Response


class APIResponse:
    @staticmethod
    def success(data=None, message="تمت العملية بنجاح", status=200):
        return Response(
            {"success": True, "message": message, "data": data}, status=status
        )

    @staticmethod
    def error(message, error_code="INTERNAL_ERROR", status=400, data=None):
        return Response(
            {
                "success": False,
                "message": message,
                "errorCode": error_code,
                "data": data,
            },
            status=status,
        )

    @staticmethod
    def paginated(queryset, request, serializer_class, context=None):
        from core.pagination import CustomPagination

        paginator = CustomPagination()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = serializer_class(page, many=True, context=context)
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "pagination": {
                        "page": paginator.page.number,
                        "limit": paginator.get_page_size(request),
                        "total": paginator.page.paginator.count,
                        "totalPages": paginator.page.paginator.num_pages,
                    },
                }
            )

        serializer = serializer_class(queryset, many=True, context=context)
        return Response({"success": True, "data": serializer.data})
