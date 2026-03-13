from sage_sias import CoresetSelector, OnlineContinualLearner, wrap_sample


def test_import_and_selector_loss_topk() -> None:
    selector = CoresetSelector(strategy="loss_topk")
    samples = [
        wrap_sample("a", "hello", loss=0.1),
        wrap_sample("b", "world", loss=0.9),
        wrap_sample("c", "foo", loss=0.4),
    ]
    selected = selector.select(samples, target_size=2)
    assert len(selected) == 2
    assert selected[0].sample_id == "b"


def test_online_continual_learner_buffer_limit() -> None:
    learner = OnlineContinualLearner(buffer_size=3, replay_ratio=0.5)
    batch1 = [wrap_sample(str(i), f"text-{i}") for i in range(3)]
    learner.update_buffer(batch1)
    batch2 = [wrap_sample("3", "text-3"), wrap_sample("4", "text-4")]
    learner.update_buffer(batch2)
    assert learner.buffer_len == 3
