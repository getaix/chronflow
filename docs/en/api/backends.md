# Backends API {#en-backends-api}

Symphra Scheduler provides multiple queue backend implementations for different scenarios.

## QueueBackend (abstract base class) {#en-backends-queuebackend}

::: symphra_scheduler.backends.base.QueueBackend
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## MemoryBackend {#en-backends-memorybackend}

::: symphra_scheduler.backends.memory.MemoryBackend
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## SQLiteBackend {#en-backends-sqlitebackend}

::: symphra_scheduler.backends.sqlite_backend.SQLiteBackend
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## RedisBackend {#en-backends-redisbackend}

::: symphra_scheduler.backends.redis_backend.RedisBackend
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## RabbitMQBackend {#en-backends-rabbitmqbackend}

::: symphra_scheduler.backends.rabbitmq_backend.RabbitMQBackend
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google