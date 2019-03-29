from flask import Blueprint
from dmutils.metrics import DMGDSMetrics


metrics = Blueprint('metrics', __name__)

gds_metrics = DMGDSMetrics()

metrics.add_url_rule(gds_metrics.metrics_path, 'metrics', gds_metrics.metrics_endpoint)
