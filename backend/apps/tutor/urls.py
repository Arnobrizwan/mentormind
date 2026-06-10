from rest_framework.routers import DefaultRouter

from .views import TutorSessionViewSet

router = DefaultRouter()
router.register("sessions", TutorSessionViewSet, basename="tutor-session")

urlpatterns = router.urls
