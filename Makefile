ANSIBLE_CONFIG := bootstrap/ansible/ansible.cfg
INVENTORY := bootstrap/ansible/inventory/hosts.yml
PLAYBOOKS := bootstrap/ansible/playbooks

export ANSIBLE_CONFIG

.PHONY: age-key greenfield join verify lint

age-key:
	@test ! -e sops_age_key.txt || { echo "sops_age_key.txt already exists" >&2; exit 1; }
	@test ! -e age.pubkey || { echo "age.pubkey already exists; refusing to replace it" >&2; exit 1; }
	@age-keygen -o sops_age_key.txt
	@age-keygen -y sops_age_key.txt > age.pubkey
	@chmod 600 sops_age_key.txt

greenfield:
	@test "$$AGE_BACKUP_CONFIRMED" = "yes" || { echo "Set AGE_BACKUP_CONFIRMED=yes after backing up sops_age_key.txt" >&2; exit 1; }
	ansible-playbook -i $(INVENTORY) $(PLAYBOOKS)/greenfield.yml -e age_private_key_backup_confirmed=true

join:
	ansible-playbook -i $(INVENTORY) $(PLAYBOOKS)/join.yml

verify:
	ansible-playbook -i $(INVENTORY) $(PLAYBOOKS)/verify.yml

lint:
	bash scripts/validate-layout.sh
	bash scripts/test-ansible-skeleton.sh
	python3 scripts/test-ansible-lockdown.py
	python3 scripts/test-ansible-docker-swarm.py
	python3 scripts/test-ansible-doco-cd.py
	python3 scripts/test-ansible-verify.py
	ansible-lint bootstrap/ansible
	ansible-playbook -i $(INVENTORY) --syntax-check $(PLAYBOOKS)/greenfield.yml
	ansible-playbook -i $(INVENTORY) --syntax-check $(PLAYBOOKS)/join.yml
	ansible-playbook -i $(INVENTORY) --syntax-check $(PLAYBOOKS)/verify.yml
