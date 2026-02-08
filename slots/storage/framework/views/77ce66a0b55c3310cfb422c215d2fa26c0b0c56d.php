<?php $__env->startSection('page-title', 'Payment form'); ?>
<?php $__env->startSection('add-main-class', 'main-redirect'); ?>
<?php $__env->startSection('add-header-class', 'main-redirect'); ?>
<?php
    $currency = auth()->user()->present()->shop ? auth()->user()->present()->shop->currency : '';
?>



<?php $__env->startSection('content'); ?>

    <?php echo $__env->make('frontend.Default.partials.header', \Illuminate\Support\Arr::except(get_defined_vars(), ['__data', '__path']))->render(); ?>

	<div class="redirect" style="background-image: url('/frontend/Default/img/_src/redirected-bg.png')">
		<h1 class="redirect__title">
			You will be rediracted to
			<span class="redirect__time">paymant page in 5-7 second!</span>

		</h1>

		<?php if( is_array($data) ): ?>
		<form action="<?php echo e($data['action']); ?>" method="<?php echo e($data['method']); ?>" id="payment_form">
			<?php echo Form::token(); ?>

			<?php $__currentLoopData = $data['fields']; $__env->addLoop($__currentLoopData); foreach($__currentLoopData as $field=>$value): $__env->incrementLoopIndices(); $loop = $__env->getLastLoop(); ?>
				<input type="hidden" name="<?php echo e($field); ?>" value="<?php echo e($value); ?>">
			<?php endforeach; $__env->popLoop(); $loop = $__env->getLastLoop(); ?>
			<button type="submit" class="btn btn--redirect" >OK</button>
		</form>
		<?php else: ?>
			<?php echo $data; ?>

		<?php endif; ?>
	</div>

<?php $__env->stopSection(); ?>

<?php $__env->startSection('footer'); ?>
	<?php echo $__env->make('frontend.Default.partials.footer', \Illuminate\Support\Arr::except(get_defined_vars(), ['__data', '__path']))->render(); ?>
<?php $__env->stopSection(); ?>

<?php $__env->startSection('scripts'); ?>
	<?php echo $__env->make('frontend.Default.partials.scripts', \Illuminate\Support\Arr::except(get_defined_vars(), ['__data', '__path']))->render(); ?>
<?php $__env->stopSection(); ?>

<?php echo $__env->make('frontend.Default.layouts.app', \Illuminate\Support\Arr::except(get_defined_vars(), ['__data', '__path']))->render(); ?><?php /**PATH /var/www/casino/resources/views/frontend/Default/payment_form.blade.php ENDPATH**/ ?>