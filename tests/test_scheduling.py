from test_main import (
    TestGetAppointmentType,
    TestGetNextFreeSlots,
    TestGetWorkingHours,
    TestIsBlocked,
)


class TestAppointmentTypes(TestGetAppointmentType):
    __test__ = True


class TestBlockedIntervals(TestIsBlocked):
    __test__ = True


class TestWorkingHours(TestGetWorkingHours):
    __test__ = True


class TestAvailableSlots(TestGetNextFreeSlots):
    __test__ = True
