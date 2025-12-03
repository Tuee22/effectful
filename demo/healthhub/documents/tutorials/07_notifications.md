# Tutorial 07: Real-Time Notifications

> Extends base [Tutorial 07: Migration Guide](../../../../documents/tutorials/07_migration_guide.md); base steps apply. This tutorial documents HealthHub-specific notification flows only.

---

## Overview

HealthHub uses Redis pub/sub for real-time notifications delivered via WebSocket. Notifications are ephemeral and only delivered to active connections.

---

## Connecting to WebSocket

### JavaScript Client

```javascript
// Connect to WebSocket endpoint
const userId = 'your-user-id';
const token = 'your-jwt-token';
const ws = new WebSocket(`wss://localhost:8851/ws/${userId}?token=${token}`);

ws.onopen = () => {
    console.log('Connected to notifications');
};

ws.onmessage = (event) => {
    const notification = JSON.parse(event.data);
    handleNotification(notification);
};

ws.onclose = () => {
    console.log('Disconnected from notifications');
    // Implement reconnection logic
};

function handleNotification(notification) {
    switch (notification.type) {
        case 'appointment_requested':
            showAppointmentRequest(notification);
            break;
        case 'appointment_status_changed':
            updateAppointmentStatus(notification);
            break;
        case 'new_prescription':
            showNewPrescription(notification);
            break;
        case 'critical_lab_result':
            showUrgentAlert(notification);
            break;
        case 'lab_result_available':
            showLabNotification(notification);
            break;
    }
}
```

### Python Client (for testing)

```python
import asyncio
import websockets

async def listen_notifications(user_id: str, token: str):
    uri = f"ws://localhost:8851/ws/{user_id}?token={token}"

    async with websockets.connect(uri) as websocket:
        print("Connected to notifications")

        async for message in websocket:
            notification = json.loads(message)
            print(f"Received: {notification}")

asyncio.run(listen_notifications("user-id", "jwt-token"))
```

---

## Notification Types

### Appointment Requested

Sent to doctor when patient requests appointment:

```json
{
    "type": "appointment_requested",
    "appointment_id": "...",
    "patient_name": "Alice Johnson",
    "reason": "Annual checkup",
    "requested_time": "2025-02-01T10:00:00Z"
}
```

### Appointment Status Changed

Sent to both patient and doctor:

```json
{
    "type": "appointment_status_changed",
    "appointment_id": "...",
    "new_status": "Confirmed",
    "scheduled_time": "2025-02-01T10:00:00Z"
}
```

### New Prescription

Sent to patient:

```json
{
    "type": "new_prescription",
    "prescription_id": "...",
    "medication": "Amoxicillin",
    "doctor_name": "Dr. Smith"
}
```

### Critical Lab Result

Sent to doctor (urgent):

```json
{
    "type": "critical_lab_result",
    "urgent": true,
    "result_id": "...",
    "patient_name": "Bob Wilson",
    "test_type": "BMP",
    "requires_review": true
}
```

### Lab Result Available

Sent to patient:

```json
{
    "type": "lab_result_available",
    "result_id": "...",
    "test_type": "CBC",
    "reviewed": false
}
```

---

## Channel Patterns

| Channel | Recipients | Example |
|---------|------------|---------|
| `doctor:{id}:notifications` | Specific doctor | `doctor:abc123:notifications` |
| `patient:{id}:notifications` | Specific patient | `patient:def456:notifications` |
| `system:alerts` | All connected users | `system:alerts` |

---

## Sending Notifications from Programs

```python
def schedule_appointment_program(...):
    # ... create appointment ...

    # Send notification to doctor
    yield PublishWebSocketNotification(
        channel=f"doctor:{doctor_id}:notifications",
        message={
            "type": "appointment_requested",
            "appointment_id": str(appointment.id),
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "reason": reason,
        },
        recipient_id=doctor_id,
    )
```

---

## Testing Notifications

### Unit Test (Mocked)

```python
def test_appointment_sends_notification() -> None:
    gen = schedule_appointment_program(
        patient_id, doctor_id, requested_time, reason, actor_id
    )

    # Step through to notification
    effect = next(gen)  # GetPatientById
    effect = gen.send(mock_patient)  # GetDoctorById
    effect = gen.send(mock_doctor)  # CreateAppointment
    effect = gen.send(mock_appointment)  # PublishWebSocketNotification

    assert isinstance(effect, PublishWebSocketNotification)
    assert effect.channel == f"doctor:{doctor_id}:notifications"
    assert effect.message["type"] == "appointment_requested"
```

### Integration Test

```python
async def test_notification_delivered(redis_client) -> None:
    # Subscribe to channel
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("doctor:test:notifications")

    # Trigger notification
    await publish_notification("doctor:test:notifications", {"type": "test"})

    # Verify delivery
    message = await pubsub.get_message(timeout=1.0)
    assert message is not None
```

---

## Reconnection Handling

WebSocket connections may drop. Implement reconnection:

```javascript
class NotificationClient {
    constructor(userId, token) {
        this.userId = userId;
        this.token = token;
        this.reconnectDelay = 1000;
        this.maxDelay = 30000;
        this.connect();
    }

    connect() {
        this.ws = new WebSocket(`wss://localhost:8851/ws/${this.userId}?token=${this.token}`);

        this.ws.onopen = () => {
            console.log('Connected');
            this.reconnectDelay = 1000; // Reset delay on success
        };

        this.ws.onclose = () => {
            console.log(`Reconnecting in ${this.reconnectDelay}ms`);
            setTimeout(() => this.connect(), this.reconnectDelay);
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxDelay);
        };

        this.ws.onmessage = (event) => {
            this.handleMessage(JSON.parse(event.data));
        };
    }

    handleMessage(notification) {
        // Handle notification
    }
}
```

---

## Next Steps

- [Tutorial 08: Testing HealthHub](08_testing_healthhub.md)
- [Notification System](../product/notification_system.md)
- [Architecture Overview](../product/architecture_overview.md)

---

**Last Updated**: 2025-11-25  
**Supersedes**: none  
**Referenced by**: ../README.md, ../engineering/websocket_security.md
